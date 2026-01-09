import json

from flask_restx import Resource, fields, reqparse

from controllers.console import api, console_ns
from controllers.console.wraps import account_initialization_required, login_required, setup_required
from extensions.ext_database import db
from extensions.ext_redis import redis_client
from libs.datetime_utils import naive_utc_now
from libs.login import current_account_with_tenant
from models import Account
from models.account import Tenant, TenantAccountJoin
from services.account_service import RegisterService, TenantService

invitation_fields = {
    "workspace_id": fields.String,
    "workspace_name": fields.String,
    "inviter_name": fields.String,
    "role": fields.String,
    "token": fields.String,
    "created_at": fields.String,
}

invitation_list_fields = {
    "invitations": fields.List(fields.Nested(api.model("InvitationInfo", invitation_fields))),
}


@console_ns.route("/workspaces/invitations")
class InvitationListApi(Resource):
    """Get all pending invitations for current user."""

    @setup_required
    @login_required
    @account_initialization_required
    @api.marshal_with(invitation_list_fields)
    def get(self):
        current_user, _ = current_account_with_tenant()
        
        # Get all pending invitations from Redis
        invitations = []
        
        # Get all tenant_account_joins where account is pending and not in current tenant
        pending_joins = (
            db.session.query(TenantAccountJoin)
            .join(Tenant, TenantAccountJoin.tenant_id == Tenant.id)
            .filter(
                TenantAccountJoin.account_id == current_user.id,
                Tenant.status == "normal"
            )
            .all()
        )
        
        # Check each join for valid invitation token in Redis
        for join in pending_joins:
            # Try to find invitation token in Redis
            # We need to scan for tokens that match this workspace and email
            cursor = 0
            pattern = "member_invite:token:*"
            
            while True:
                try:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    for key in keys:
                        try:
                            data = redis_client.get(key)
                            if data:
                                invitation_data = json.loads(data)
                                # Check if this invitation matches
                                if (invitation_data.get("email") == current_user.email and 
                                    invitation_data.get("workspace_id") == join.tenant_id):
                                    tenant = db.session.query(Tenant).filter_by(id=join.tenant_id).first()
                                    if tenant:
                                        # Get inviter info (first owner/admin of the workspace)
                                        owner_join = (
                                            db.session.query(TenantAccountJoin)
                                            .filter_by(tenant_id=join.tenant_id)
                                            .order_by(TenantAccountJoin.created_at.asc())
                                            .first()
                                        )
                                        inviter_name = "系统管理员"
                                        role = join.role
                                        if owner_join:
                                            inviter_account = db.session.query(Account).filter_by(
                                                id=owner_join.account_id
                                            ).first()
                                            if inviter_account:
                                                inviter_name = inviter_account.name
                                        
                                        # Extract token from key
                                        token = key.decode().replace("member_invite:token:", "")
                                        
                                        invitations.append({
                                            "workspace_id": join.tenant_id,
                                            "workspace_name": tenant.name,
                                            "inviter_name": inviter_name,
                                            "role": role,
                                            "token": token,
                                            "created_at": tenant.created_at.isoformat() if tenant.created_at else "",
                                        })
                                        break
                        except Exception:
                            continue
                    
                    if cursor == 0:
                        break
                except Exception:
                    break
        
        return {"invitations": invitations}, 200


accept_invitation_parser = reqparse.RequestParser().add_argument(
    "token", type=str, required=True, nullable=False, location="json"
)


@console_ns.route("/workspaces/invitations/accept")
class AcceptInvitationApi(Resource):
    """Accept a workspace invitation."""

    @api.expect(accept_invitation_parser)
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        args = accept_invitation_parser.parse_args()
        current_user, _ = current_account_with_tenant()
        
        # Get invitation data
        invitation_data = RegisterService.get_invitation_by_token(args["token"])
        if not invitation_data:
            return {"message": "Invalid invitation token"}, 400
        
        # Verify invitation is for current user
        if invitation_data.get("email") != current_user.email:
            return {"message": "This invitation is not for your account"}, 400
        
        workspace_id = invitation_data.get("workspace_id")
        tenant = db.session.query(Tenant).filter_by(id=workspace_id).first()
        if not tenant:
            return {"message": "Workspace not found"}, 404
        
        # Check if user is already a member
        existing_join = (
            db.session.query(TenantAccountJoin)
            .filter_by(tenant_id=workspace_id, account_id=current_user.id)
            .first()
        )
        
        if existing_join:
            # User is already a member, just switch to this workspace
            TenantService.switch_tenant(current_user, workspace_id)
            # Revoke token
            RegisterService.revoke_token(workspace_id, current_user.email, args["token"])
            return {"result": "success", "message": "Already a member, switched to workspace"}, 200
        
        # Get role from existing tenant_account_join or create new one
        tenant_account_join = (
            db.session.query(TenantAccountJoin)
            .filter_by(tenant_id=workspace_id, account_id=current_user.id)
            .first()
        )
        
        if not tenant_account_join:
            # Create tenant member if not exists (role should be from invitation, but we use normal as default)
            TenantService.create_tenant_member(tenant, current_user, role="normal")
        
        # Activate account if pending
        if current_user.status == "pending":
            current_user.status = "active"
            current_user.initialized_at = naive_utc_now()
        
        # Switch to the invited workspace
        TenantService.switch_tenant(current_user, workspace_id)
        
        # Revoke token
        RegisterService.revoke_token(workspace_id, current_user.email, args["token"])
        
        db.session.commit()
        
        return {"result": "success", "workspace_id": workspace_id}, 200

