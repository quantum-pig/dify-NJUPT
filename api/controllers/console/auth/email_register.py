from flask import request
from flask_restx import Resource
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from configs import dify_config
from constants.languages import languages
from controllers.console import console_ns
from controllers.console.auth.error import (
    EmailAlreadyInUseError,
    EmailCodeError,
    EmailRegisterLimitError,
    InvalidEmailError,
    InvalidInvitationCodeError,
    InvalidTokenError,
    PasswordMismatchError,
)
from extensions.ext_database import db
from libs.helper import EmailStr, extract_remote_ip
from libs.password import valid_password
from models import Account
from services.account_service import AccountService
from services.billing_service import BillingService
from services.errors.account import AccountNotFoundError, AccountRegisterError

from ..error import AccountInFreezeError, EmailSendIpLimitError
from ..wraps import email_password_login_enabled, email_register_enabled

DEFAULT_REF_TEMPLATE_SWAGGER_2_0 = "#/definitions/{model}"


class EmailRegisterSendPayload(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    language: str | None = Field(default=None, description="Language code")


class EmailRegisterValidityPayload(BaseModel):
    email: EmailStr = Field(...)
    code: str = Field(...)
    token: str = Field(...)


class EmailRegisterResetPayload(BaseModel):
    token: str | None = Field(default=None, description="Registration token (for email verification flow)")
    email: EmailStr | None = Field(default=None, description="Email address (for invitation code flow)")
    new_password: str = Field(...)
    password_confirm: str = Field(...)
    invitation_code: str | None = Field(default=None, description="Invitation code (for direct registration)")
    workspace_name: str | None = Field(default=None, description="Workspace name")

    @field_validator("new_password", "password_confirm")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return valid_password(value)


for model in (EmailRegisterSendPayload, EmailRegisterValidityPayload, EmailRegisterResetPayload):
    console_ns.schema_model(model.__name__, model.model_json_schema(ref_template=DEFAULT_REF_TEMPLATE_SWAGGER_2_0))


@console_ns.route("/email-register/send-email")
class EmailRegisterSendEmailApi(Resource):
    @email_password_login_enabled
    @email_register_enabled
    def post(self):
        args = EmailRegisterSendPayload.model_validate(console_ns.payload)

        ip_address = extract_remote_ip(request)
        if AccountService.is_email_send_ip_limit(ip_address):
            raise EmailSendIpLimitError()
        language = "en-US"
        if args.language in languages:
            language = args.language

        if dify_config.BILLING_ENABLED and BillingService.is_email_in_freeze(args.email):
            raise AccountInFreezeError()

        with Session(db.engine) as session:
            account = session.execute(select(Account).filter_by(email=args.email)).scalar_one_or_none()
        token = None
        token = AccountService.send_email_register_email(email=args.email, account=account, language=language)
        return {"result": "success", "data": token}


@console_ns.route("/email-register/validity")
class EmailRegisterCheckApi(Resource):
    @email_password_login_enabled
    @email_register_enabled
    def post(self):
        args = EmailRegisterValidityPayload.model_validate(console_ns.payload)

        user_email = args.email

        is_email_register_error_rate_limit = AccountService.is_email_register_error_rate_limit(args.email)
        if is_email_register_error_rate_limit:
            raise EmailRegisterLimitError()

        token_data = AccountService.get_email_register_data(args.token)
        if token_data is None:
            raise InvalidTokenError()

        if user_email != token_data.get("email"):
            raise InvalidEmailError()

        if args.code != token_data.get("code"):
            AccountService.add_email_register_error_rate_limit(args.email)
            raise EmailCodeError()

        # Verified, revoke the first token
        AccountService.revoke_email_register_token(args.token)

        # Refresh token data by generating a new token
        _, new_token = AccountService.generate_email_register_token(
            user_email, code=args.code, additional_data={"phase": "register"}
        )

        AccountService.reset_email_register_error_rate_limit(args.email)
        return {"is_valid": True, "email": token_data.get("email"), "token": new_token}


@console_ns.route("/email-register")
class EmailRegisterResetApi(Resource):
    @email_password_login_enabled
    @email_register_enabled
    def post(self):
        args = EmailRegisterResetPayload.model_validate(console_ns.payload)

        # Validate passwords match
        if args.new_password != args.password_confirm:
            raise PasswordMismatchError()

        email = None
        # Support two registration modes:
        # 1. Token-based (official flow with email verification)
        # 2. Invitation code-based (custom flow without email verification)
        if args.token:
            # Official token-based flow
            register_data = AccountService.get_email_register_data(args.token)
            if not register_data:
                raise InvalidTokenError()
            # Must use token in reset phase
            if register_data.get("phase", "") != "register":
                raise InvalidTokenError()
            # Revoke token to prevent reuse
            AccountService.revoke_email_register_token(args.token)
            email = register_data.get("email", "")
        elif args.invitation_code:
            # Custom invitation code-based flow
            if args.invitation_code != "njupt2025":
                raise InvalidInvitationCodeError()
            # Email should be provided directly in invitation code flow
            if not args.email:
                raise InvalidEmailError("Email is required for invitation code registration.")
            email = args.email
        else:
            raise InvalidTokenError("Either token or invitation_code must be provided")

        with Session(db.engine) as session:
            account = session.execute(select(Account).filter_by(email=email)).scalar_one_or_none()

            if account:
                raise EmailAlreadyInUseError()
            else:
                # Use workspace_name from args if provided, otherwise use email prefix
                workspace_name = args.workspace_name or email.split("@")[0]
                account = self._create_new_account(email, args.new_password, workspace_name)
                if not account:
                    raise AccountNotFoundError()
                token_pair = AccountService.login(account=account, ip_address=extract_remote_ip(request))
                AccountService.reset_login_error_rate_limit(email)

        return {"result": "success", "data": token_pair.model_dump()}

    def _create_new_account(self, email: str, password: str, workspace_name: str) -> Account | None:
        # Create new account if allowed
        account = None
        try:
            account = AccountService.create_account_and_tenant(
                email=email,
                name=workspace_name,
                password=password,
                interface_language=languages[0],
                workspace_name=workspace_name
            )
        except AccountRegisterError:
            raise AccountInFreezeError()

        return account
