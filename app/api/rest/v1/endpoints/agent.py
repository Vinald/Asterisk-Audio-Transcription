from fastapi import APIRouter, Form, HTTPException, status

from app.services import chat

router = APIRouter(
    prefix="/agent",
    tags=["Pipeline"],
    responses={
        400: {"description": "Bad request or agent error"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Process text with the AI agent",
    description="Send a text message to the Hashie AI agent and receive a reply.",
    responses={
        200: {
            "description": "Agent reply",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "input_text": "I have a headache",
                        "agent_response": "How long have you had the headache?",
                        "language": "eng",
                        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        }
    },
)
async def process_with_agent(
    text: str = Form(..., description="User message to send to the agent."),
    language: str = Form("eng", description="Language code for the conversation (default: eng)."),
    conversation_id: str = Form(
        None,
        description=(
            "Pass the conversation_id from a previous response to continue the same thread. "
            "Omit to start a new conversation."
        ),
    ),
):
    """
    Send a text message to the Hashie AI agent:

    - **text**: The user's input message
    - **language**: Language code used to guide the agent's response (e.g. eng, lug, ach)
    - **conversation_id**: Thread identifier — omit to start a new conversation, pass the
      value returned by a previous call to continue an existing one
    """
    try:
        response, returned_conversation_id = chat(text, language, conversation_id)
        return {
            "success": True,
            "input_text": text,
            "agent_response": response,
            "language": language,
            "conversation_id": returned_conversation_id,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
