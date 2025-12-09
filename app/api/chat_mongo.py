from fastapi import APIRouter, HTTPException, Depends
from app.models.mongo_models import User, Conversation, Message
from app.api.auth_mongo import get_current_user_mongo
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.translation_service import TranslationService
from app.services.student_service import StudentDataService
from datetime import datetime
from beanie import PydanticObjectId
from typing import Optional

router = APIRouter(prefix="/chat/mongo", tags=["MongoDB Chat"])

# Initialize services
rag_service = RAGService()
llm_service = LLMService()
translation_service = TranslationService()
student_service = StudentDataService()


@router.post("/", response_model=ChatResponse)
async def chat_mongo(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_mongo)
):
    """Chat endpoint using MongoDB for conversation storage."""
    try:
        # Translate to English if needed
        original_language = request.language
        if request.language == "hi":
            question_en = await translation_service.translate(request.message, "hi", "en")
        else:
            question_en = request.message
        
        # Get or create conversation
        if request.conversation_id and request.conversation_id != 0:
            conversation = await Conversation.get(PydanticObjectId(str(request.conversation_id)))
            if not conversation or conversation.user_id != str(current_user.id):
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation = Conversation(
                user_id=str(current_user.id),
                university_id=request.university_id,
                messages=[]
            )
            await conversation.insert()
        
        # Retrieve relevant context using RAG
        context_docs = await rag_service.retrieve_context(
            query=question_en,
            top_k=5,
            university_id=request.university_id
        )
        
        context_text = "\n\n".join([doc.get("text", "") for doc in context_docs])
        sources = [doc.get("source", "unknown") for doc in context_docs]
        
        # Build conversation history
        messages = []
        for msg in conversation.messages[-5:]:  # Last 5 messages for context
            messages.append({
                "role": "user" if msg.is_user else "assistant",
                "content": msg.content
            })
        
        # Get data from MongoDB based on user role
        user_role = getattr(current_user, 'role', 'USER')
        organization_id = getattr(current_user, 'organization', None)
        
        student_summary = await student_service.get_student_summary(
            current_user.email, 
            current_user.full_name or current_user.email.split('@')[0],
            user_role,
            organization_id,
            user_id=str(current_user.id)
        )
        
        # Create personalized system prompt with user info, student data, and context
        user_info = f"User: {current_user.full_name} ({current_user.email})\n\n{student_summary}"
        personalized_context = f"{user_info}\n\n{context_text}"
        system_prompt = llm_service.create_system_prompt(personalized_context, original_language)
        
        # Add personalized greeting for first message
        if len(conversation.messages) == 0:
            system_prompt += f"\n\nThis is your first conversation with {current_user.full_name}. Greet them warmly by name and ask how you can help them today."
        
        # Add system prompt and current question
        llm_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
            {"role": "user", "content": question_en}
        ]
        
        # Generate response
        response_en = await llm_service.generate_response(llm_messages)
        
        # Translate response if needed
        if original_language == "hi":
            response = await translation_service.translate(response_en, "en", "hi")
        else:
            response = response_en
        
        # Save messages to conversation
        user_message = Message(
            content=request.message,
            is_user=True,
            language=original_language,
            sources=[]
        )
        
        assistant_message = Message(
            content=response,
            is_user=False,
            language=original_language,
            sources=sources
        )
        
        conversation.messages.append(user_message)
        conversation.messages.append(assistant_message)
        conversation.updated_at = datetime.utcnow()
        
        await conversation.save()
        
        return ChatResponse(
            conversation_id=str(conversation.id),
            message=response,
            response=response,
            language=original_language,
            sources=sources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_conversations(current_user: User = Depends(get_current_user_mongo)):
    """Get all conversations for ONLY the current logged-in user."""
    # IMPORTANT: Only fetch conversations belonging to this specific user
    conversations = await Conversation.find(
        {"user_id": str(current_user.id)}
    ).sort("-updated_at").to_list()
    
    return {
        "user": {
            "name": current_user.full_name,
            "email": current_user.email
        },
        "conversations": [
            {
                "id": str(conv.id),
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": len(conv.messages),
                "preview": conv.messages[0].content if conv.messages else "Empty conversation"
            }
            for conv in conversations
        ]
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user_mongo)
):
    """Get a specific conversation - ONLY if it belongs to the logged-in user."""
    conversation = await Conversation.get(PydanticObjectId(conversation_id))
    
    # SECURITY CHECK: Ensure user can only access their own conversations
    if not conversation or conversation.user_id != str(current_user.id):
        raise HTTPException(
            status_code=404, 
            detail="Conversation not found or you don't have permission to access it"
        )
    
    return {
        "user": current_user.full_name,
        "conversation": {
            "id": str(conversation.id),
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "messages": [
                {
                    "content": msg.content,
                    "is_user": msg.is_user,
                    "timestamp": msg.timestamp,
                    "language": msg.language,
                    "sources": msg.sources
                }
                for msg in conversation.messages
            ]
        }
    }


@router.post("/public", response_model=ChatResponse)
async def chat_public(request: ChatRequest):
    """Public chat endpoint for anonymous users - NO authentication required."""
    try:
        # Translate to English if needed
        original_language = request.language
        if request.language == "hi":
            question_en = await translation_service.translate(request.message, "hi", "en")
        else:
            question_en = request.message
        
        # Retrieve relevant context using RAG
        context_docs = await rag_service.retrieve_context(
            query=question_en,
            top_k=5,
            university_id=request.university_id
        )
        
        context_text = "\n\n".join([doc.get("text", "") for doc in context_docs])
        sources = [doc.get("source", "unknown") for doc in context_docs]
        
        # Create public system prompt (no personal info)
        public_system_prompt = f"""You are SatyaSetu AI Assistant, a helpful chatbot for the SatyaSetu Educational Document Verification System.

Your role:
- Provide general information about SatyaSetu certificate verification system
- Explain how the blockchain-based verification works
- Help users understand certificate authenticity and security
- Guide users on how to verify certificates
- Answer questions about educational document verification
- Explain the benefits of digital certificates

Important Guidelines:
- You are speaking to a GUEST USER (not logged in)
- DO NOT show any personal certificate data or student information
- Encourage users to login for personalized certificate information
- Be helpful, professional, and informative
- If asked about specific certificates, tell them to login first

Context from knowledge base:
{context_text}

Respond in {original_language} language."""
        
        # Generate response
        llm_messages = [
            {"role": "system", "content": public_system_prompt},
            {"role": "user", "content": question_en}
        ]
        
        response_en = await llm_service.generate_response(llm_messages)
        
        # Translate response if needed
        if original_language == "hi":
            response = await translation_service.translate(response_en, "en", "hi")
        else:
            response = response_en
        
        # Return response without saving to database (anonymous user)
        return ChatResponse(
            conversation_id="0",  # No conversation for anonymous users
            message=response,
            sources=sources,
            language=original_language
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
