from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import httpx
import json

load_dotenv()

app = FastAPI(title="Digital Wallet API")

# CORS middleware
# Get allowed origins from environment or use defaults
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Validate environment variables
if not supabase_url:
    raise ValueError("SUPABASE_URL environment variable is not set. Please check your .env file.")
if not supabase_service_key:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set. Please check your .env file.")

supabase: Client = create_client(supabase_url, supabase_service_key)

# Helper function to get user by email from users table
def get_user_by_email(email: str):
    """Get user by email from users table"""
    try:
        result = supabase.table("users").select("id, email, full_name, created_at").eq("email", email).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        # If table doesn't exist, return None gracefully
        if "Could not find the table" in str(e) or "PGRST205" in str(e):
            print("WARNING: users table does not exist. Please run the SQL script to create it.")
        return None

# Helper function to get user by ID from users table
def get_user_by_id(user_id: str):
    """Get user by ID from users table"""
    try:
        result = supabase.table("users").select("id, email, full_name, created_at").eq("id", user_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        # If table doesn't exist, return None gracefully
        if "Could not find the table" in str(e) or "PGRST205" in str(e):
            print("WARNING: users table does not exist. Please run the SQL script to create it.")
        return None


# Pydantic models
class TransferRequest(BaseModel):
    recipient_email: EmailStr
    amount: float


class TransactionResponse(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: float
    created_at: str
    from_user_email: Optional[str] = None
    to_user_email: Optional[str] = None


class BalanceResponse(BaseModel):
    balance: float


class TransactionsResponse(BaseModel):
    transactions: List[TransactionResponse]


class PendingTransactionResponse(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: float
    status: str
    violations: List[str]
    created_at: str
    from_user_email: Optional[str] = None
    to_user_email: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None


class ApproveTransactionRequest(BaseModel):
    transaction_id: str
    approve: bool


# Dependency to verify JWT token and get user from users table
async def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        token = authorization.replace("Bearer ", "")
        # Verify token with Supabase using REST API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": supabase_service_key,
                    "Authorization": f"Bearer {token}"
                }
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            auth_user_data = response.json()
            user_id = auth_user_data.get("id")
            auth_email = auth_user_data.get("email")
            
            # Try to get user from users table, but fallback to auth data if table doesn't exist
            user_data = get_user_by_id(user_id)
            if not user_data:
                # If users table doesn't exist or user not found, use auth data
                # This allows the system to work even if users table isn't set up yet
                print(f"Warning: User {user_id} not found in users table, using auth data")
                user_data = {
                    "id": user_id,
                    "email": auth_email,
                    "full_name": None
                }
            
            # Create a simple user object
            class User:
                def __init__(self, user_data):
                    self.id = user_data.get("id")
                    self.email = user_data.get("email")
                    self.full_name = user_data.get("full_name")
            return User(user_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


@app.get("/")
def read_root():
    return {"message": "Digital Wallet API"}


@app.get("/api/balance", response_model=BalanceResponse)
async def get_balance(user=Depends(verify_token)):
    try:
        # Get user's wallet balance
        wallet = supabase.table("wallets").select("balance").eq("user_id", user.id).execute()
        
        if not wallet.data:
            # Create wallet if it doesn't exist
            supabase.table("wallets").insert({
                "user_id": user.id,
                "balance": 1000.0  # Starting balance
            }).execute()
            return BalanceResponse(balance=1000.0)
        
        balance = wallet.data[0]["balance"]
        return BalanceResponse(balance=balance)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_balance: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error fetching balance: {str(e)}")


@app.get("/api/transactions", response_model=TransactionsResponse)
async def get_transactions(user=Depends(verify_token)):
    try:
        # Get all transactions where user is sender or receiver
        transactions = supabase.table("transactions").select(
            "id, from_user_id, to_user_id, amount, created_at"
        ).or_(
            f"from_user_id.eq.{user.id},to_user_id.eq.{user.id}"
        ).order("created_at", desc=True).limit(50).execute()
        
        # Get pending transactions for this user
        pending_transactions = []
        try:
            pending_result = supabase.table("pending_transactions").select("*").eq(
                "from_user_id", user.id
            ).eq("status", "pending").order("created_at", desc=True).execute()
            
            if pending_result.data:
                pending_transactions = pending_result.data
        except:
            pass  # If table doesn't exist, continue without pending
        
        # Get all unique user IDs from transactions (batch query instead of N queries)
        all_user_ids = set()
        if transactions.data:
            for tx in transactions.data:
                all_user_ids.add(tx["from_user_id"])
                all_user_ids.add(tx["to_user_id"])
        
        # Batch fetch all user emails in one query
        user_email_map = {}
        if all_user_ids:
            try:
                users_batch = supabase.table("users").select("id, email").in_("id", list(all_user_ids)).execute()
                user_email_map = {user["id"]: user["email"] for user in users_batch.data}
            except:
                pass  # If table doesn't exist, continue without emails
        
        # Build transaction list with emails from map
        transaction_list = []
        if transactions.data:
            for tx in transactions.data:
                from_email = user_email_map.get(tx["from_user_id"])
                to_email = user_email_map.get(tx["to_user_id"])
                
                transaction_list.append(TransactionResponse(
                    id=tx["id"],
                    from_user_id=tx["from_user_id"],
                    to_user_id=tx["to_user_id"],
                    amount=tx["amount"],
                    created_at=tx["created_at"],
                    from_user_email=from_email,
                    to_user_email=to_email
                ))
        
        # Add pending transactions (use same email map)
        for pending_tx in pending_transactions:
            # Add to_user_id to map if not already there
            if pending_tx["to_user_id"] not in user_email_map:
                try:
                    to_user_data = get_user_by_id(pending_tx["to_user_id"])
                    if to_user_data:
                        user_email_map[pending_tx["to_user_id"]] = to_user_data.get("email")
                except:
                    pass
            
            to_email = user_email_map.get(pending_tx["to_user_id"])
            
            # Create a transaction response with pending status indicator
            transaction_list.append(TransactionResponse(
                id=f"pending_{pending_tx['id']}",  # Prefix to identify as pending
                from_user_id=pending_tx["from_user_id"],
                to_user_id=pending_tx["to_user_id"],
                amount=float(pending_tx["amount"]),
                created_at=pending_tx["created_at"],
                from_user_email=user.email,  # Current user
                to_user_email=to_email
            ))
        
        # Sort by created_at descending
        transaction_list.sort(key=lambda x: x.created_at, reverse=True)
        
        return TransactionsResponse(transactions=transaction_list)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_transactions: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")


@app.post("/api/transfer")
async def transfer_money(request: TransferRequest, user=Depends(verify_token)):
    try:
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Get recipient user by email from users table
        recipient_user = get_user_by_email(request.recipient_email)
        
        if not recipient_user:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        recipient_user_id = recipient_user.get("id")
        if recipient_user_id == user.id:
            raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
        
        # Get sender's wallet
        sender_wallet = supabase.table("wallets").select("balance").eq("user_id", user.id).execute()
        if not sender_wallet.data:
            # Create wallet if it doesn't exist
            supabase.table("wallets").insert({
                "user_id": user.id,
                "balance": 1000.0
            }).execute()
            sender_balance = 1000.0
        else:
            sender_balance = sender_wallet.data[0]["balance"]
        
        if sender_balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Action Blocker acts as adapter - decides auto-approve or flag for review
        # All transaction processing goes through Action Blocker
        action_blocker_url = os.getenv("ACTION_BLOCKER_URL", "http://127.0.0.1:8001")
        action_blocker_url_clean = action_blocker_url.rstrip('/')
        
        try:
            # Call Action Blocker to process transaction
            # Action Blocker will:
            # - Check rules
            # - If no violations → Auto-approve and execute immediately
            # - If violations → Flag for admin review
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                process_response = await client.post(
                    f"{action_blocker_url_clean}/api/process-transaction",
                    json={
                        "from_user_id": user.id,
                        "to_user_id": recipient_user_id,
                        "amount": request.amount,
                        "sender_balance": sender_balance
                    },
                    timeout=30.0
                )
                
                if process_response.status_code == 200:
                    result = process_response.json()
                    print(f"✅ Action Blocker processed transaction: {result.get('status')}")
                    return result
                else:
                    error_msg = process_response.text
                    print(f"❌ Action Blocker error: {process_response.status_code} - {error_msg}")
                    raise HTTPException(
                        status_code=process_response.status_code,
                        detail=f"Action Blocker Service error: {error_msg}"
                    )
                    
        except httpx.TimeoutException:
            error_msg = "Action Blocker Service timeout - transaction blocked for safety"
            print(f"❌ {error_msg}")
            # Block transaction for safety when service is down
            try:
                pending_tx = supabase.table("pending_transactions").insert({
                    "from_user_id": user.id,
                    "to_user_id": recipient_user_id,
                    "amount": request.amount,
                    "status": "pending",
                    "violations": json.dumps(["Action Blocker Service timeout - blocked for safety"])
                }).execute()
                return {
                    "message": "Transaction blocked - Action Blocker Service timeout",
                    "status": "pending",
                    "pending_transaction_id": pending_tx.data[0]["id"],
                    "violations": ["Action Blocker Service timeout - blocked for safety"],
                    "requires_approval": True
                }
            except:
                raise HTTPException(status_code=503, detail=error_msg)
        except httpx.ConnectError:
            error_msg = "Action Blocker Service is not reachable - transaction blocked for safety"
            print(f"❌ {error_msg}")
            # Block transaction for safety when service is down
            try:
                pending_tx = supabase.table("pending_transactions").insert({
                    "from_user_id": user.id,
                    "to_user_id": recipient_user_id,
                    "amount": request.amount,
                    "status": "pending",
                    "violations": json.dumps(["Action Blocker Service not reachable - blocked for safety"])
                }).execute()
                return {
                    "message": "Transaction blocked - Action Blocker Service not reachable",
                    "status": "pending",
                    "pending_transaction_id": pending_tx.data[0]["id"],
                    "violations": ["Action Blocker Service not reachable - blocked for safety"],
                    "requires_approval": True
                }
            except:
                raise HTTPException(status_code=503, detail=error_msg)
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Error calling Action Blocker Service: {str(e)}"
            print(f"❌ {error_msg}")
            # Block transaction for safety on any error
            try:
                pending_tx = supabase.table("pending_transactions").insert({
                    "from_user_id": user.id,
                    "to_user_id": recipient_user_id,
                    "amount": request.amount,
                    "status": "pending",
                    "violations": json.dumps([f"Action Blocker Service error: {str(e)}"])
                }).execute()
                return {
                    "message": "Transaction blocked - Action Blocker Service error",
                    "status": "pending",
                    "pending_transaction_id": pending_tx.data[0]["id"],
                    "violations": [f"Action Blocker Service error: {str(e)}"],
                    "requires_approval": True
                }
            except:
                raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in transfer_money: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")


# Admin endpoints - only accessible by admin user
@app.get("/api/admin/users")
async def get_all_users(user=Depends(verify_token)):
    # Check if user is admin
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get all users from users table
        users_result = supabase.table("users").select("id, email, full_name, created_at").execute()
        
        # Get all wallets in one query (much faster than N queries)
        user_ids = [user["id"] for user in users_result.data]
        wallets_result = supabase.table("wallets").select("user_id, balance").in_("user_id", user_ids).execute() if user_ids else {"data": []}
        
        # Create a map of user_id -> balance for fast lookup
        balance_map = {wallet["user_id"]: float(wallet["balance"]) for wallet in wallets_result.data}
        
        # Combine users with balances
        users_with_balances = []
        for user_data in users_result.data:
            balance = balance_map.get(user_data["id"], 0.0)
            users_with_balances.append({
                **user_data,
                "balance": balance
            })
        
        return {"users": users_with_balances}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_all_users: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@app.get("/api/admin/transactions")
async def get_all_transactions(user=Depends(verify_token)):
    # Check if user is admin
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get all completed transactions
        transactions_result = supabase.table("transactions").select(
            "id, from_user_id, to_user_id, amount, created_at"
        ).order("created_at", desc=True).limit(100).execute()
        
        # Get rejected transactions from pending_transactions
        rejected_result = []
        try:
            rejected_result = supabase.table("pending_transactions").select("*").eq(
                "status", "rejected"
            ).order("created_at", desc=True).limit(100).execute()
        except:
            pass  # If table doesn't exist, continue without rejected
        
        # Get all unique user IDs from transactions (batch query instead of N queries)
        all_user_ids = set()
        if transactions_result.data:
            for tx in transactions_result.data:
                all_user_ids.add(tx["from_user_id"])
                all_user_ids.add(tx["to_user_id"])
        
        # Batch fetch all user emails in one query
        user_email_map = {}
        if all_user_ids:
            users_batch = supabase.table("users").select("id, email").in_("id", list(all_user_ids)).execute()
            user_email_map = {user["id"]: user["email"] for user in users_batch.data}
        
        # Build transaction list with emails from map
        transaction_list = []
        if transactions_result.data:
            for tx in transactions_result.data:
                from_email = user_email_map.get(tx["from_user_id"])
                to_email = user_email_map.get(tx["to_user_id"])
                
                transaction_list.append({
                    "id": tx["id"],
                    "from_user_id": tx["from_user_id"],
                    "to_user_id": tx["to_user_id"],
                    "amount": tx["amount"],
                    "created_at": tx["created_at"],
                    "from_user_email": from_email,
                    "to_user_email": to_email,
                    "status": "completed"
                })
        
        # Add rejected transactions (use same email map)
        if rejected_result and rejected_result.data:
            # Add any missing user IDs to the map
            for tx in rejected_result.data:
                if tx["from_user_id"] not in user_email_map:
                    all_user_ids.add(tx["from_user_id"])
                if tx["to_user_id"] not in user_email_map:
                    all_user_ids.add(tx["to_user_id"])
            
            # Fetch any missing users
            missing_ids = [uid for uid in all_user_ids if uid not in user_email_map]
            if missing_ids:
                missing_users = supabase.table("users").select("id, email").in_("id", missing_ids).execute()
                for user in missing_users.data:
                    user_email_map[user["id"]] = user["email"]
            
            for tx in rejected_result.data:
                from_email = user_email_map.get(tx["from_user_id"])
                to_email = user_email_map.get(tx["to_user_id"])
                
                # Parse violations JSON
                violations = []
                if tx.get("violations"):
                    try:
                        violations = json.loads(tx["violations"]) if isinstance(tx["violations"], str) else tx["violations"]
                    except:
                        violations = []
                
                transaction_list.append({
                    "id": f"rejected_{tx['id']}",  # Prefix to identify as rejected
                    "from_user_id": tx["from_user_id"],
                    "to_user_id": tx["to_user_id"],
                    "amount": float(tx["amount"]),
                    "created_at": tx["created_at"],
                    "from_user_email": from_email,
                    "to_user_email": to_email,
                    "status": "rejected",
                    "violations": violations,
                    "reviewed_at": tx.get("reviewed_at"),
                    "reviewed_by": tx.get("reviewed_by")
                })
        
        # Sort by created_at descending
        transaction_list.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {"transactions": transaction_list}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_all_transactions: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")


# Pending transactions endpoints for admin
@app.get("/api/admin/pending-transactions")
async def get_pending_transactions(user=Depends(verify_token)):
    """Get all pending transactions awaiting approval"""
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        pending_result = supabase.table("pending_transactions").select("*").eq(
            "status", "pending"
        ).order("created_at", desc=True).execute()
        
        # Batch fetch user emails (much faster than N queries)
        all_user_ids = set()
        if pending_result.data:
            for tx in pending_result.data:
                all_user_ids.add(tx["from_user_id"])
                all_user_ids.add(tx["to_user_id"])
        
        user_email_map = {}
        if all_user_ids:
            try:
                users_batch = supabase.table("users").select("id, email").in_("id", list(all_user_ids)).execute()
                user_email_map = {user["id"]: user["email"] for user in users_batch.data}
            except:
                pass
        
        pending_list = []
        if pending_result.data:
            for tx in pending_result.data:
                from_email = user_email_map.get(tx["from_user_id"])
                to_email = user_email_map.get(tx["to_user_id"])
                
                # Parse violations JSON
                violations = []
                if tx.get("violations"):
                    try:
                        violations = json.loads(tx["violations"]) if isinstance(tx["violations"], str) else tx["violations"]
                    except:
                        violations = []
                
                pending_list.append({
                    "id": tx["id"],
                    "from_user_id": tx["from_user_id"],
                    "to_user_id": tx["to_user_id"],
                    "amount": float(tx["amount"]),
                    "status": tx["status"],
                    "violations": violations,
                    "created_at": tx["created_at"],
                    "from_user_email": from_email,
                    "to_user_email": to_email,
                    "reviewed_at": tx.get("reviewed_at"),
                    "reviewed_by": tx.get("reviewed_by")
                })
        
        return {"pending_transactions": pending_list}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_pending_transactions: {str(e)}")
        print(f"Traceback: {error_details}")
        # If table doesn't exist, return empty list
        if "Could not find the table" in str(e) or "PGRST205" in str(e):
            return {"pending_transactions": []}
        raise HTTPException(status_code=500, detail=f"Error fetching pending transactions: {str(e)}")


@app.post("/api/admin/approve-transaction")
async def approve_transaction(request: ApproveTransactionRequest, user=Depends(verify_token)):
    """Approve or reject a pending transaction"""
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get pending transaction - check all statuses to handle edge cases
        pending_result = supabase.table("pending_transactions").select("*").eq(
            "id", request.transaction_id
        ).execute()
        
        if not pending_result.data or len(pending_result.data) == 0:
            raise HTTPException(status_code=404, detail="Pending transaction not found")
        
        pending_tx = pending_result.data[0]
        current_status = pending_tx.get("status", "pending")
        
        # If already approved/rejected, don't process again
        if current_status == "approved" and request.approve:
            return {
                "message": "Transaction already approved",
                "status": "approved",
                "transaction_id": request.transaction_id
            }
        if current_status == "rejected" and not request.approve:
            return {
                "message": "Transaction already rejected",
                "status": "rejected"
            }
        
        # Only process if status is pending
        if current_status != "pending":
            raise HTTPException(status_code=400, detail=f"Transaction is already {current_status}, cannot change status")
        
        print(f"🔄 Processing {'approval' if request.approve else 'rejection'} for transaction {request.transaction_id}")
        
        # All approval/rejection decisions go through Action Blocker Service
        # Action Blocker is the central authority for all approval decisions
        action_blocker_url = os.getenv("ACTION_BLOCKER_URL", "http://127.0.0.1:8001")
        action_blocker_url_clean = action_blocker_url.rstrip('/')
        
        try:
            # Call Action Blocker Service to handle approval/rejection
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                approve_response = await client.post(
                    f"{action_blocker_url_clean}/api/approve-transaction",
                    json={
                        "transaction_id": request.transaction_id,
                        "approve": request.approve,
                        "reviewed_by": user.id,
                        "review_notes": None
                    },
                    timeout=30.0
                )
                
                if approve_response.status_code == 200:
                    result = approve_response.json()
                    print(f"✅ Action Blocker processed approval: {result.get('status')}")
                    return result
                else:
                    error_msg = approve_response.text
                    print(f"❌ Action Blocker error: {approve_response.status_code} - {error_msg}")
                    raise HTTPException(
                        status_code=approve_response.status_code,
                        detail=f"Action Blocker Service error: {error_msg}"
                    )
                    
        except httpx.TimeoutException:
            error_msg = "Action Blocker Service timeout - cannot process approval"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=503, detail=error_msg)
        except httpx.ConnectError:
            error_msg = "Action Blocker Service is not reachable - cannot process approval"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=503, detail=error_msg)
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Error calling Action Blocker Service: {str(e)}"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in approve_transaction: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error processing approval: {str(e)}")


@app.get("/api/admin/rules")
async def get_rules(user=Depends(verify_token)):
    """Get all transaction rules"""
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Query rules directly from database
        rules_result = supabase.table("transaction_rules").select("*").execute()
        rules = rules_result.data if rules_result.data else []
        return {"rules": rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rules: {str(e)}")


class UpdateRuleRequest(BaseModel):
    rule_id: str
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


@app.post("/api/admin/rules/update")
async def update_rule(request: UpdateRuleRequest, user=Depends(verify_token)):
    """Update a rule's configuration or enabled status"""
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get rule from database
        rule_result = supabase.table("transaction_rules").select("*").eq(
            "rule_id", request.rule_id
        ).execute()
        
        if not rule_result.data or len(rule_result.data) == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        rule_data = rule_result.data[0]
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        # Update enabled status if provided
        if request.enabled is not None:
            update_data["enabled"] = request.enabled
        
        # Update config if provided
        if request.config is not None:
            # Merge with existing config
            existing_config = rule_data.get("rule_config", {})
            if isinstance(existing_config, str):
                existing_config = json.loads(existing_config)
            existing_config.update(request.config)
            update_data["rule_config"] = existing_config
        
        # Update in database
        supabase.table("transaction_rules").update(update_data).eq(
            "rule_id", request.rule_id
        ).execute()
        
        # Note: Action Blocker Service will reload rules on its own when needed
        # No need to reload here since we delegate all rule checking to action-blocker
        
        return {"message": "Rule updated successfully", "rule_id": request.rule_id}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error updating rule: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error updating rule: {str(e)}")


# Action Blocker Service management
_action_blocker_service = None

@app.post("/api/admin/action-blocker/start")
async def start_action_blocker(user=Depends(verify_token)):
    """Start the Action Blocker Service"""
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    global _action_blocker_service
    
    try:
        # Check if external service is running first
        action_blocker_url = os.getenv("ACTION_BLOCKER_URL", "http://127.0.0.1:8001")
        
        try:
            action_blocker_url_clean = action_blocker_url.rstrip('/')
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{action_blocker_url_clean}/api/status", timeout=2.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("running"):
                        return {
                            "message": "External Action Blocker Service is already running",
                            "status": "running",
                            "url": action_blocker_url
                        }
        except:
            pass  # External service not running, continue with internal service
        
        # Import the service for internal mode
        import sys
        import os
        action_blocker_path = os.path.join(os.path.dirname(__file__), '..', 'action-blocker')
        sys.path.insert(0, action_blocker_path)
        from action_blocker_service import ActionBlockerService
        
        if _action_blocker_service is None:
            # Get host and port from env or use defaults
            host = os.getenv("ACTION_BLOCKER_HOST", "127.0.0.1")
            port = int(os.getenv("ACTION_BLOCKER_PORT", "8001"))
            _action_blocker_service = ActionBlockerService(host=host, port=port)
        
        if _action_blocker_service.running:
            return {"message": "Service is already running", "status": "running"}
        
        if _action_blocker_service.start():
            return {
                "message": "Action Blocker Service started successfully",
                "status": "running",
                "url": f"http://{_action_blocker_service.host}:{_action_blocker_service.port}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start service")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error starting action blocker: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error starting service: {str(e)}")


@app.post("/api/admin/action-blocker/stop")
async def stop_action_blocker(user=Depends(verify_token)):
    """Stop the Action Blocker Service"""
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    global _action_blocker_service
    
    if _action_blocker_service is None or not _action_blocker_service.running:
        return {"message": "Service is not running", "status": "stopped"}
    
    try:
        _action_blocker_service.stop()
        return {"message": "Action Blocker Service stopped successfully", "status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping service: {str(e)}")


@app.get("/api/admin/action-blocker/status")
async def get_action_blocker_status(user=Depends(verify_token)):
    """Get Action Blocker Service status"""
    if user.email != "admin@admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    global _action_blocker_service
    
    # First, try to check external service
    action_blocker_url = os.getenv("ACTION_BLOCKER_URL", "http://127.0.0.1:8001")
    
    try:
        action_blocker_url_clean = action_blocker_url.rstrip('/')
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(f"{action_blocker_url_clean}/api/status", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    **data,
                    "url": action_blocker_url,
                    "mode": "external"
                }
    except Exception as e:
        # External service not available, check internal
        pass
    
    # Check internal service
    if _action_blocker_service is None:
        return {
            "status": "stopped",
            "running": False,
            "rules_count": 0,
            "active_rules": 0,
            "mode": "internal",
            "url": action_blocker_url
        }
    
    try:
        status = _action_blocker_service.get_status()
        return {
            "status": "running" if status["running"] else "stopped",
            **status,
            "mode": "internal",
            "url": f"http://{_action_blocker_service.host}:{_action_blocker_service.port}"
        }
    except Exception as e:
        return {
            "status": "error",
            "running": False,
            "error": str(e),
            "mode": "internal"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

