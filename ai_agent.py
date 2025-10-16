"""
AI Agent for Agency Project Builder
Provides natural language interface to control the UI and execute commands
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel

# Import OpenAI for natural language understanding
try:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
except Exception as e:
    print(f"[AI Agent] OpenAI not available: {e}")
    OPENAI_AVAILABLE = False
    client = None

# Import GPT-5 helpers if available
try:
    from gpt5_helpers import gpt5_text
    from openai import OpenAI
    sync_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    GPT5_AVAILABLE = True
except Exception:
    GPT5_AVAILABLE = False
    sync_client = None

class CommandType(str, Enum):
    """Types of commands the agent can execute"""
    UPLOAD_RFP = "upload_rfp"
    ANALYZE_RFP = "analyze_rfp"
    SELECT_DELIVERABLES = "select_deliverables"
    MODIFY_PRICING = "modify_pricing"
    SET_RETAINER = "set_retainer"
    SET_BUDGET = "set_budget"
    ADD_MARKUP = "add_markup"
    OPTIMIZE_TIMELINE = "optimize_timeline"
    EXPORT_PROJECT = "export_project"
    NAVIGATE = "navigate"
    CLEAR_DATA = "clear_data"
    REMOVE_DELIVERABLES = "remove_deliverables"
    EXTEND_TIMELINE = "extend_timeline"
    UNKNOWN = "unknown"

@dataclass
class ParsedCommand:
    """Parsed user command with intent and parameters"""
    command_type: CommandType
    parameters: Dict[str, Any]
    confidence: float
    raw_text: str
    explanation: str = ""
    
@dataclass
class UIAction:
    """Represents a UI action to be executed"""
    action_type: str  # 'click', 'fill', 'select', 'scroll', 'wait'
    target: str       # CSS selector or element ID
    value: Any = None # Value for fill/select actions
    description: str = ""

class AgentChatRequest(BaseModel):
    """Request model for agent chat endpoint"""
    message: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    gpt5_tier: Optional[str] = "auto"  # auto, mini, thinking-mini, thinking, pro

class AgentExecuteRequest(BaseModel):
    """Request model for agent execute endpoint"""
    command: str
    parameters: Dict[str, Any]
    auto_execute: bool = True

class AgentResponse(BaseModel):
    """Response model for agent endpoints"""
    success: bool
    message: str
    command: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    result: Optional[Any] = None
    error: Optional[str] = None

# Agent conversation history (in-memory for now)
AGENT_CONVERSATIONS = {}

async def parse_user_intent(message: str, context: Optional[Dict] = None, gpt5_tier: str = "auto") -> ParsedCommand:
    """Parse user intent from natural language using GPT-5 with tier selection
    
    CHARLES AGENT: ProBuFo (Progressive Business Forecasting Oracle)
    The preeminent executive project manager AI assistant
    """
    
    if not OPENAI_AVAILABLE:
        return ParsedCommand(
            command_type=CommandType.UNKNOWN,
            parameters={},
            confidence=0.0,
            raw_text=message,
            explanation="CHARLES AGENT requires OpenAI API access"
        )
    
    # Build context-aware prompt
    system_prompt = """You are an AI agent for the Agency Project Builder app. Parse the user's intent and extract command parameters.

Available commands:
1. UPLOAD_RFP: Upload or paste RFP content
2. ANALYZE_RFP: Analyze RFP with AI (fast/deep mode)
3. SELECT_DELIVERABLES: Select/deselect specific deliverables
4. MODIFY_PRICING: Change pricing for deliverables (hours, rates, or total price)
5. SET_RETAINER: Set monthly retainer pricing
6. SET_BUDGET: Set total project budget
7. ADD_MARKUP: Add percentage markup to deliverables
8. OPTIMIZE_TIMELINE: Optimize project timeline
9. EXPORT_PROJECT: Export to Excel or MS Project
10. NAVIGATE: Navigate to a specific step (1-4)
11. CLEAR_DATA: Clear all data and start fresh
12. REMOVE_DELIVERABLES: Remove specific deliverables
13. EXTEND_TIMELINE: Extend timeline by days/weeks

Parse the user message and return a JSON object with:
{
    "command_type": "COMMAND_TYPE",
    "parameters": {
        // relevant parameters based on command
    },
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation of what will be done"
}

For MODIFY_PRICING, parameters should include:
- "target": deliverable name or code
- "price": new price (if setting price)
- "hours": new hours (if setting hours)
- "rate": new rate (if setting rate)
- "is_monthly": true if monthly retainer

For SET_RETAINER, parameters should include:
- "deliverable": deliverable name or code
- "monthly_amount": monthly price
- "months": number of months

For ADD_MARKUP, parameters should include:
- "percentage": markup percentage
- "target": "all", "creative", "strategy", etc.

For EXTEND_TIMELINE, parameters should include:
- "duration": number of days/weeks
- "unit": "days" or "weeks"
"""

    user_prompt = f"User message: {message}"
    if context:
        user_prompt += f"\n\nCurrent context: {json.dumps(context)}"
    
    try:
        if GPT5_AVAILABLE and sync_client:
            # Map user-selected tier to GPT-5 models
            # For now, map all to "mini" as it's most reliable
            tier_mapping = {
                "auto": "mini",  # Fast parsing by default
                "mini": "mini",
                "thinking-mini": "mini",  # Map to actual model
                "thinking": "mini",  # Use mini for now
                "pro": "mini"  # Use mini for now until pro is fixed
            }
            selected_tier = tier_mapping.get(gpt5_tier, "mini")
            
            # Use selected GPT-5 tier for intent parsing
            print(f"[CHARLES] Using GPT-5 tier: {selected_tier} (from input: {gpt5_tier})")
            
            # Add JSON instruction to the system prompt
            json_system_prompt = system_prompt + "\n\nIMPORTANT: You must respond with valid JSON only, no other text."
            
            # Add timeout handling
            import signal
            
            class TimeoutException(Exception):
                pass
            
            def timeout_handler(signum, frame):
                raise TimeoutException("GPT-5 API call timed out after 15 seconds")
            
            # Set timeout alarm
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(15)  # 15 second timeout
            
            try:
                response = gpt5_text(
                    sync_client,
                    messages=[
                        {"role": "system", "content": json_system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    tier=selected_tier,
                    max_output_tokens=500,
                    use_retry=False  # Disable retry for faster response
                )
                signal.alarm(0)  # Cancel the alarm
            except TimeoutException as te:
                print(f"[CHARLES] GPT-5 timeout: {te}")
                signal.alarm(0)  # Cancel the alarm
                raise Exception(str(te))
            
            if response:
                print(f"[CHARLES] GPT-5 response received, parsing JSON...")
                # Try to extract JSON from response even if it has extra text
                try:
                    # First try direct parse
                    parsed = json.loads(response)
                except json.JSONDecodeError:
                    # Try to find JSON in the response
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                    else:
                        raise ValueError(f"No valid JSON found in response: {response[:200]}...")
                
                # Log the parsed command for debugging
                print(f"[CHARLES] Parsed command: {parsed.get('command_type', 'UNKNOWN')} with confidence: {parsed.get('confidence', 0)}")
                
                # Handle case variations in command type
                cmd_type = parsed.get("command_type", "UNKNOWN").upper()
                try:
                    # Try to match with enum values
                    command_type = CommandType[cmd_type]
                except (KeyError, ValueError):
                    # Try lowercase version
                    try:
                        command_type = CommandType(cmd_type.lower())
                    except (KeyError, ValueError):
                        command_type = CommandType.UNKNOWN
                
                return ParsedCommand(
                    command_type=command_type,
                    parameters=parsed.get("parameters", {}),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_text=message,
                    explanation=parsed.get("explanation", "")
                )
        else:
            # Fallback to GPT-4 if GPT-5 not available
            response = await client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.3
            )
            
            parsed = json.loads(response.choices[0].message.content)
            return ParsedCommand(
                command_type=CommandType(parsed.get("command_type", "UNKNOWN")),
                parameters=parsed.get("parameters", {}),
                confidence=float(parsed.get("confidence", 0.5)),
                raw_text=message,
                explanation=parsed.get("explanation", "")
            )
            
    except Exception as e:
        print(f"[Agent] Failed to parse intent: {e}")
        
        # Fallback to rule-based parsing
        return fallback_intent_parser(message)

def fallback_intent_parser(message: str) -> ParsedCommand:
    """Rule-based fallback parser for when AI is not available"""
    print(f"[CHARLES] Using fallback parser for message: {message[:50]}...")
    msg_lower = message.lower()
    
    # Simple pattern matching
    if any(word in msg_lower for word in ['upload', 'paste', 'rfp', 'brief']):
        return ParsedCommand(
            command_type=CommandType.UPLOAD_RFP,
            parameters={},
            confidence=0.6,
            raw_text=message,
            explanation="Upload or paste RFP content"
        )
    
    elif any(word in msg_lower for word in ['analyze', 'process', 'scan']):
        mode = "deep" if "deep" in msg_lower else "fast"
        return ParsedCommand(
            command_type=CommandType.ANALYZE_RFP,
            parameters={"mode": mode},
            confidence=0.7,
            raw_text=message,
            explanation=f"Analyze RFP in {mode} mode"
        )
    
    elif 'retainer' in msg_lower or 'monthly' in msg_lower:
        # Extract price if present
        price_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', message)
        price = float(price_match.group(1).replace(',', '')) if price_match else 10000
        
        return ParsedCommand(
            command_type=CommandType.SET_RETAINER,
            parameters={
                "monthly_amount": price,
                "months": 12
            },
            confidence=0.5,
            raw_text=message,
            explanation=f"Set monthly retainer at ${price:,.0f}"
        )
    
    elif 'budget' in msg_lower:
        # Extract budget amount
        budget_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:k|m)?)', msg_lower)
        if budget_match:
            budget_str = budget_match.group(1).replace(',', '')
            if 'k' in budget_str:
                budget = float(budget_str.replace('k', '')) * 1000
            elif 'm' in budget_str:
                budget = float(budget_str.replace('m', '')) * 1000000
            else:
                budget = float(budget_str)
                
            return ParsedCommand(
                command_type=CommandType.SET_BUDGET,
                parameters={"budget": budget},
                confidence=0.6,
                raw_text=message,
                explanation=f"Set budget to ${budget:,.0f}"
            )
    
    elif 'markup' in msg_lower:
        # Extract percentage
        pct_match = re.search(r'(\d{1,3})%?', message)
        percentage = float(pct_match.group(1)) if pct_match else 20
        
        target = "all"
        if 'creative' in msg_lower:
            target = "creative"
        elif 'strategy' in msg_lower:
            target = "strategy"
            
        return ParsedCommand(
            command_type=CommandType.ADD_MARKUP,
            parameters={
                "percentage": percentage,
                "target": target
            },
            confidence=0.6,
            raw_text=message,
            explanation=f"Add {percentage}% markup to {target} deliverables"
        )
    
    elif 'remove' in msg_lower or 'delete' in msg_lower:
        return ParsedCommand(
            command_type=CommandType.REMOVE_DELIVERABLES,
            parameters={},
            confidence=0.5,
            raw_text=message,
            explanation="Remove deliverables"
        )
    
    elif 'extend' in msg_lower and 'timeline' in msg_lower:
        # Extract duration
        duration_match = re.search(r'(\d+)\s*(week|day)', msg_lower)
        if duration_match:
            duration = int(duration_match.group(1))
            unit = duration_match.group(2) + 's'
            
            return ParsedCommand(
                command_type=CommandType.EXTEND_TIMELINE,
                parameters={
                    "duration": duration,
                    "unit": unit
                },
                confidence=0.6,
                raw_text=message,
                explanation=f"Extend timeline by {duration} {unit}"
            )
    
    elif 'export' in msg_lower:
        format = "excel" if "excel" in msg_lower else "xml"
        return ParsedCommand(
            command_type=CommandType.EXPORT_PROJECT,
            parameters={"format": format},
            confidence=0.7,
            raw_text=message,
            explanation=f"Export project as {format.upper()}"
        )
    
    elif 'clear' in msg_lower or 'reset' in msg_lower:
        return ParsedCommand(
            command_type=CommandType.CLEAR_DATA,
            parameters={},
            confidence=0.6,
            raw_text=message,
            explanation="Clear all data and start fresh"
        )
    
    # Default unknown
    return ParsedCommand(
        command_type=CommandType.UNKNOWN,
        parameters={},
        confidence=0.0,
        raw_text=message,
        explanation="Unable to understand command"
    )

def generate_ui_actions(command: ParsedCommand) -> List[UIAction]:
    """Generate UI actions to execute the parsed command"""
    actions = []
    
    if command.command_type == CommandType.UPLOAD_RFP:
        actions.extend([
            UIAction("scroll", "window", {"top": 0}, "Scroll to top"),
            UIAction("focus", "#rfpText", None, "Focus on RFP text area"),
            UIAction("highlight", "#rfpText", None, "Highlight RFP input area")
        ])
    
    elif command.command_type == CommandType.ANALYZE_RFP:
        mode = command.parameters.get("mode", "fast")
        mode_btn_id = "#mode-fast" if mode == "fast" else "#mode-deep"
        
        actions.extend([
            UIAction("click", mode_btn_id, None, f"Select {mode} mode"),
            UIAction("wait", None, 500, "Wait for mode selection"),
            UIAction("click", "#btnAnalyze", None, "Click Analyze button"),
        ])
    
    elif command.command_type == CommandType.SELECT_DELIVERABLES:
        # This would require specific deliverable IDs from the context
        deliverable = command.parameters.get("deliverable")
        if deliverable:
            actions.append(
                UIAction("toggle", f"[data-deliverable='{deliverable}']", None, f"Toggle {deliverable}")
            )
    
    elif command.command_type == CommandType.MODIFY_PRICING:
        target = command.parameters.get("target")
        
        if command.parameters.get("price"):
            actions.extend([
                UIAction("find", f"[data-deliverable-code='{target}']", None, f"Find {target}"),
                UIAction("fill", f"[data-price-input='{target}']", 
                        command.parameters["price"], f"Set price to ${command.parameters['price']}")
            ])
        
        if command.parameters.get("hours"):
            actions.extend([
                UIAction("fill", f"[data-hours-input='{target}']", 
                        command.parameters["hours"], f"Set hours to {command.parameters['hours']}")
            ])
    
    elif command.command_type == CommandType.SET_RETAINER:
        deliverable = command.parameters.get("deliverable")
        amount = command.parameters.get("monthly_amount", 10000)
        
        actions.extend([
            UIAction("find", f"[data-deliverable='{deliverable}']", None, f"Find {deliverable}"),
            UIAction("check", f"[data-retainer-checkbox='{deliverable}']", None, "Enable retainer"),
            UIAction("fill", f"[data-retainer-amount='{deliverable}']", amount, f"Set to ${amount}/month")
        ])
    
    elif command.command_type == CommandType.SET_BUDGET:
        budget = command.parameters.get("budget", 500000)
        actions.extend([
            UIAction("scroll", "#step3", None, "Scroll to pricing step"),
            UIAction("fill", "#total-budget", budget, f"Set budget to ${budget:,.0f}"),
            UIAction("click", "#optimize-budget", None, "Optimize to budget")
        ])
    
    elif command.command_type == CommandType.ADD_MARKUP:
        percentage = command.parameters.get("percentage", 20)
        target = command.parameters.get("target", "all")
        
        actions.extend([
            UIAction("scroll", "#step3", None, "Scroll to pricing step"),
            UIAction("fill", "#markup-percentage", percentage, f"Set markup to {percentage}%"),
            UIAction("select", "#markup-target", target, f"Select {target} deliverables"),
            UIAction("click", "#apply-markup", None, "Apply markup")
        ])
    
    elif command.command_type == CommandType.OPTIMIZE_TIMELINE:
        actions.extend([
            UIAction("scroll", "#step4", None, "Scroll to timeline step"),
            UIAction("click", "#btn-generate-timeline", None, "Generate timeline"),
        ])
    
    elif command.command_type == CommandType.EXPORT_PROJECT:
        format = command.parameters.get("format", "excel")
        btn_id = "#btn-export-excel" if format == "excel" else "#btn-export-xml"
        
        actions.extend([
            UIAction("scroll", "#step4", None, "Scroll to export section"),
            UIAction("click", btn_id, None, f"Export as {format.upper()}")
        ])
    
    elif command.command_type == CommandType.CLEAR_DATA:
        actions.extend([
            UIAction("click", "#btnClearAllData", None, "Click clear data button"),
            UIAction("confirm", None, None, "Confirm data clearing")
        ])
    
    elif command.command_type == CommandType.EXTEND_TIMELINE:
        duration = command.parameters.get("duration", 7)
        unit = command.parameters.get("unit", "days")
        
        actions.extend([
            UIAction("scroll", "#step4", None, "Scroll to timeline"),
            UIAction("execute", "extendTimeline", {"duration": duration, "unit": unit}, 
                    f"Extend timeline by {duration} {unit}")
        ])
    
    return actions

async def chat_with_agent(message: str, context: Optional[Dict] = None, session_id: Optional[str] = None, gpt5_tier: str = "auto") -> AgentResponse:
    """Process a chat message and return agent response using CHARLES AGENT: ProBuFo"""
    
    # Parse user intent with GPT-5 tier
    command = await parse_user_intent(message, context, gpt5_tier)
    
    # Generate UI actions
    actions = generate_ui_actions(command)
    
    # Store conversation history
    if session_id:
        if session_id not in AGENT_CONVERSATIONS:
            AGENT_CONVERSATIONS[session_id] = []
        
        AGENT_CONVERSATIONS[session_id].append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": message,
            "command": command.__dict__,
            "actions": [a.__dict__ for a in actions]
        })
    
    # Prepare response
    if command.command_type == CommandType.UNKNOWN:
        response_message = f"I didn't understand that command. {command.explanation}\n\nTry commands like:\n• 'Analyze the RFP in deep mode'\n• 'Set Creative Strategy to $10k monthly'\n• 'Add 20% markup to all deliverables'\n• 'Export to Excel'"
    else:
        response_message = command.explanation
        if actions:
            response_message += f"\n\n📋 I'll execute {len(actions)} actions to complete this task."
    
    return AgentResponse(
        success=command.command_type != CommandType.UNKNOWN,
        message=response_message,
        command={
            "type": command.command_type.value,
            "parameters": command.parameters,
            "confidence": command.confidence
        },
        actions=[{
            "type": a.action_type,
            "target": a.target,
            "value": a.value,
            "description": a.description
        } for a in actions]
    )

async def execute_command(command_type: str, parameters: Dict[str, Any]) -> AgentResponse:
    """Execute a specific command with given parameters"""
    
    try:
        cmd = ParsedCommand(
            command_type=CommandType(command_type),
            parameters=parameters,
            confidence=1.0,
            raw_text="Direct execution"
        )
        
        actions = generate_ui_actions(cmd)
        
        return AgentResponse(
            success=True,
            message=f"Executed {command_type} command",
            actions=[{
                "type": a.action_type,
                "target": a.target,
                "value": a.value,
                "description": a.description
            } for a in actions],
            result={"executed": True, "action_count": len(actions)}
        )
        
    except Exception as e:
        return AgentResponse(
            success=False,
            message=f"Failed to execute command: {str(e)}",
            error=str(e)
        )

# Export functions for use in main.py
__all__ = [
    'AgentChatRequest',
    'AgentExecuteRequest', 
    'AgentResponse',
    'chat_with_agent',
    'execute_command'
]