import base64
import secrets

from flask_restx import Resource, fields

from controllers.console import api, console_ns
from controllers.console.wraps import account_initialization_required, login_required, setup_required
from extensions.ext_database import db
from libs.login import current_account_with_tenant
from libs.password import hash_password, valid_password
from models import Account
from models.account import AccountStatus
from models.model import DifySetup
from services.errors.account import AccountNotFoundError

account_fields = {
    "id": fields.String,
    "name": fields.String,
    "email": fields.String,
    "status": fields.String,
    "created_at": fields.DateTime,
    "last_login_at": fields.DateTime,
    "initialized_at": fields.DateTime,
}


def is_initial_admin(account: Account) -> bool:
    """Check if account is the initial admin (setup account)"""
    # Get the first account created during setup
    setup = db.session.query(DifySetup).first()
    if not setup:
        return False
    
    # Get all accounts ordered by created_at
    first_account = (
        db.session.query(Account)
        .order_by(Account.created_at.asc())
        .first()
    )
    
    if not first_account:
        return False
    
    return first_account.id == account.id


@console_ns.route("/admin/users")
class AdminUserListApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @api.marshal_with(api.model("AdminUserListResponse", {"users": fields.List(fields.Nested(api.model("AccountInfo", account_fields)))}))
    def get(self):
        """Get all users (only initial admin can access)"""
        current_user, _ = current_account_with_tenant()
        
        if not is_initial_admin(current_user):
            return {"message": "Only initial admin can access this endpoint"}, 403
        
        # Get all accounts
        accounts = db.session.query(Account).order_by(Account.created_at.desc()).all()
        
        users = []
        for account in accounts:
            users.append({
                "id": account.id,
                "name": account.name,
                "email": account.email,
                "status": account.status,
                "created_at": account.created_at,
                "last_login_at": account.last_login_at,
                "initialized_at": account.initialized_at,
            })
        
        return {"users": users}, 200


@console_ns.route("/admin/users/<uuid:user_id>/ban")
class AdminUserBanApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, user_id):
        """Ban a user (only initial admin can access)"""
        current_user, _ = current_account_with_tenant()
        
        if not is_initial_admin(current_user):
            return {"message": "Only initial admin can access this endpoint"}, 403
        
        account = db.session.query(Account).filter_by(id=str(user_id)).first()
        if not account:
            raise AccountNotFoundError()
        
        if account.id == current_user.id:
            return {"message": "Cannot ban yourself"}, 400
        
        account.status = AccountStatus.CLOSED
        db.session.commit()
        
        return {"result": "success"}, 200


@console_ns.route("/admin/users/<uuid:user_id>/unban")
class AdminUserUnbanApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, user_id):
        """Unban a user (only initial admin can access)"""
        current_user, _ = current_account_with_tenant()
        
        if not is_initial_admin(current_user):
            return {"message": "Only initial admin can access this endpoint"}, 403
        
        account = db.session.query(Account).filter_by(id=str(user_id)).first()
        if not account:
            raise AccountNotFoundError()
        
        account.status = AccountStatus.ACTIVE
        db.session.commit()
        
        return {"result": "success"}, 200


@console_ns.route("/admin/users/<uuid:user_id>/reset-password")
class AdminUserResetPasswordApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, user_id):
        """Reset user password to njupt2025 (only initial admin can access)"""
        current_user, _ = current_account_with_tenant()
        
        if not is_initial_admin(current_user):
            return {"message": "Only initial admin can access this endpoint"}, 403
        
        account = db.session.query(Account).filter_by(id=str(user_id)).first()
        if not account:
            raise AccountNotFoundError()
        
        # Reset password to njupt2025
        new_password = "njupt2025"
        valid_password(new_password)
        
        # Generate password salt
        salt = secrets.token_bytes(16)
        base64_salt = base64.b64encode(salt).decode()
        
        # Encrypt password with salt
        password_hashed = hash_password(new_password, salt)
        base64_password_hashed = base64.b64encode(password_hashed).decode()
        
        account.password = base64_password_hashed
        account.password_salt = base64_salt
        db.session.commit()
        
        return {"result": "success"}, 200

