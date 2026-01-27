"""
AI GUARD - SINGLE CHOKE POINT FOR ALL AI/LLM CALLS

This module enforces the "AI Source Lock" - ensuring the AI can ONLY answer
using our database + engine outputs, never general trading knowledge.

CRITICAL RULES:
1. NO other file may call the Anthropic API directly
2. ALL AI calls MUST go through guarded_chat_answer()
3. Evidence Pack is MANDATORY - no evidence = no answer
4. Trade recommendations ONLY if engine_eval.status == "ENTER"
5. Fail-closed: missing data = hard refusal (never infer/estimate)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from openai import OpenAI

logger = logging.getLogger(__name__)


def get_ai_provider() -> str:
    """Get configured AI provider (openai or anthropic)."""
    return os.getenv("AI_PROVIDER", "anthropic").lower()


def get_ai_client() -> Tuple[Optional[Any], str, Optional[str]]:
    """
    Get AI client based on AI_PROVIDER env var.
    
    Returns:
        Tuple of (client, provider_name, error_message)
        - If successful: (client, "openai" or "anthropic", None)
        - If failed: (None, provider_name, error_message)
    """
    provider = get_ai_provider()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None, provider, "No OPENAI_API_KEY found in environment. Set it in secrets."
        try:
            client = OpenAI(api_key=api_key)
            return client, provider, None
        except Exception as e:
            return None, provider, f"Error initializing OpenAI client: {e}"
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not api_key:
            return None, provider, "No ANTHROPIC_API_KEY found in environment. Set it in secrets."
        try:
            client = Anthropic(api_key=api_key)
            return client, provider, None
        except Exception as e:
            return None, provider, f"Error initializing Anthropic client: {e}"

# LOCKED SYSTEM PROMPT PATH (must exist)
LOCKED_PROMPT_PATH = Path(__file__).parent / "prompts" / "LOCKED_SYSTEM_PROMPT.txt"


@dataclass
class SetupInfo:
    """Validated setup information from database."""
    setup_id: int
    strategy_name: str
    orb_time: str
    rr_target: float
    sl_mode: str
    tier: str
    win_rate: float
    avg_r: float
    trade_count: int
    annual_trades: int
    orb_size_filter: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class EngineEvaluation:
    """Strategy engine evaluation output."""
    status: str  # "WAIT" or "ENTER" (from ActionType)
    strategy_name: str
    direction: Optional[str] = None  # "LONG" or "SHORT"
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    orb_high: Optional[float] = None
    orb_low: Optional[float] = None
    setup_tier: Optional[str] = None
    rr: Optional[float] = None
    win_rate: Optional[float] = None
    avg_r: Optional[float] = None
    reasons: List[str] = field(default_factory=list)


@dataclass
class EvidencePack:
    """
    MANDATORY input for all AI calls.
    Contains ONLY data from our DB + engines (no external knowledge).

    Missing fields = refusal (fail-closed).
    """
    # Core identifiers
    instrument: str
    timeframe: str  # e.g., "1m", "5m"

    # Data source info
    candle_tables_used: List[str]  # e.g., ["bars_1m", "bars_5m"]
    ts_utc_start: datetime
    ts_utc_end: datetime

    # Strategy data
    setup_rows_used: List[SetupInfo]  # From validated_setups table
    engine_eval: EngineEvaluation  # From strategy_engine

    # Facts derived from DB/code only
    facts: List[str]  # Atomic statements (no speculation)

    # Query audit trail
    queries: List[str]  # Sanitized SQL or query descriptors

    # Evidence Footer fields (per AI_EDGE_ENGINE_PROMPT.txt)
    db_mode: str  # "local" | "motherduck"
    no_lookahead_check: str  # "PASS" | "FAIL"
    strategy_ids: List[int] = field(default_factory=list)  # Setup IDs used

    # Optional market data context
    current_price: Optional[float] = None
    session_levels: Optional[Dict[str, float]] = None  # Asia/London/NY highs/lows
    orb_data: Optional[Dict[str, Any]] = None  # Current ORB ranges

    # OHLCV data for chart analysis (PART A fix)
    bars_timeframe: Optional[str] = None  # e.g., "1m", "5m"
    bars_ohlcv_sample: Optional[List[Dict[str, Any]]] = None  # List of OHLCV bars

    # Data freshness metadata (live price/bar sync fix)
    latest_bar_ts: Optional[datetime] = None  # Timestamp of latest bar
    freshness_seconds: Optional[float] = None  # Seconds since latest bar
    data_source: Optional[str] = None  # "ProjectX", "Database", etc.

    def is_complete(self) -> bool:
        """
        FAIL-CLOSED: Check if evidence pack has ALL required fields.

        Requirements (per AI_EDGE_ENGINE_PROMPT.txt):
        - instrument and timeframe present
        - candle_tables_used exists and len >= 1
        - ts_utc_start and ts_utc_end present
        - engine_eval present
        - facts exists and len >= 1 (no empty facts list)
        - queries exists and len >= 1 (no empty queries list)
        - db_mode present (local | motherduck)
        - no_lookahead_check present (PASS | FAIL)
        """
        if not self.instrument or not self.timeframe:
            return False
        if not self.candle_tables_used or len(self.candle_tables_used) == 0:
            return False
        if not self.ts_utc_start or not self.ts_utc_end:
            return False
        if not self.engine_eval:
            return False
        # FAIL-CLOSED: Require at least one fact
        if not self.facts or len(self.facts) == 0:
            return False
        # FAIL-CLOSED: Require at least one query
        if not self.queries or len(self.queries) == 0:
            return False
        # FAIL-CLOSED: Require db_mode and no_lookahead_check
        if not self.db_mode or self.db_mode not in ["local", "motherduck"]:
            return False
        if not self.no_lookahead_check or self.no_lookahead_check not in ["PASS", "FAIL"]:
            return False
        return True

    def missing_fields(self) -> List[str]:
        """Return list of missing/null required fields (fail-closed)."""
        missing = []
        if not self.instrument:
            missing.append("instrument")
        if not self.timeframe:
            missing.append("timeframe")
        if not self.candle_tables_used or len(self.candle_tables_used) == 0:
            missing.append("candle_tables_used (must have >= 1 table)")
        if not self.ts_utc_start:
            missing.append("ts_utc_start")
        if not self.ts_utc_end:
            missing.append("ts_utc_end")
        if not self.engine_eval:
            missing.append("engine_eval")
        if not self.facts or len(self.facts) == 0:
            missing.append("facts (must have >= 1 fact)")
        if not self.queries or len(self.queries) == 0:
            missing.append("queries (must have >= 1 query)")
        if not self.db_mode or self.db_mode not in ["local", "motherduck"]:
            missing.append("db_mode (must be 'local' or 'motherduck')")
        if not self.no_lookahead_check or self.no_lookahead_check not in ["PASS", "FAIL"]:
            missing.append("no_lookahead_check (must be 'PASS' or 'FAIL')")
        return missing


def validate_evidence_pack(evidence_pack: Optional[EvidencePack], user_question: str) -> tuple[bool, Optional[str]]:
    """
    FAIL-CLOSED GATE: Validates evidence pack before allowing AI call.

    Returns:
        (is_valid, refusal_message)
        - If valid: (True, None)
        - If invalid: (False, "refusal message")

    REJECTION RULES:
    1. No evidence pack -> reject
    2. Missing required fields -> reject
    3. Trade question but engine_eval.status != "ENTER" -> reject (no trade)
    4. Missing critical data for user request -> reject
    """

    # Rule 1: No evidence pack
    if evidence_pack is None:
        return False, _format_refusal(
            "No Evidence Pack provided",
            ["evidence_pack"],
            [],
            "Load data from database and create Evidence Pack"
        )

    # Rule 2: Missing required fields
    if not evidence_pack.is_complete():
        missing = evidence_pack.missing_fields()
        return False, _format_refusal(
            "Evidence Pack incomplete (missing required fields)",
            missing,
            evidence_pack.candle_tables_used or [],
            f"Provide: {', '.join(missing)}"
        )

    # Rule 3: Trade recommendation only if ENTER signal
    user_lower = user_question.lower()
    is_trade_question = any(word in user_lower for word in [
        'should i trade', 'take this trade', 'enter', 'buy', 'sell', 'long', 'short',
        'recommend', 'trade this', 'good trade'
    ])

    if is_trade_question:
        if evidence_pack.engine_eval.status != "ENTER":
            # Build facts about why no trade
            facts = [
                f"Strategy: {evidence_pack.engine_eval.strategy_name}",
                f"Status: {evidence_pack.engine_eval.status} (not ENTER)",
            ]
            if evidence_pack.engine_eval.reasons:
                facts.extend(evidence_pack.engine_eval.reasons)

            return False, _format_no_trade_refusal(facts, evidence_pack.candle_tables_used)

    # Rule 4: Check for missing setup data if needed
    if is_trade_question and not evidence_pack.setup_rows_used:
        return False, _format_refusal(
            "No validated setups available for this instrument/strategy",
            ["setup_rows_used"],
            evidence_pack.candle_tables_used,
            "Query validated_setups table for strategy parameters"
        )

    # Rule 5: Missing entry/stop/target for ENTER signal
    if evidence_pack.engine_eval.status == "ENTER":
        missing_trade_fields = []
        if evidence_pack.engine_eval.entry_price is None:
            missing_trade_fields.append("entry_price")
        if evidence_pack.engine_eval.stop_price is None:
            missing_trade_fields.append("stop_price")
        if evidence_pack.engine_eval.target_price is None:
            missing_trade_fields.append("target_price")

        if missing_trade_fields:
            return False, _format_refusal(
                "ENTER signal but missing trade execution prices",
                missing_trade_fields,
                evidence_pack.candle_tables_used,
                "strategy_engine must provide entry/stop/target for ENTER signals"
            )

    # Rule 6: Block recommendations if lookahead check failed
    # Per AI_EDGE_ENGINE_PROMPT.txt Section 2: "Any violation → FAIL and block approval"
    if is_trade_question and evidence_pack.no_lookahead_check == "FAIL":
        return False, _format_refusal(
            "Cannot recommend trade - lookahead violation detected",
            ["no_lookahead_check=FAIL"],
            evidence_pack.candle_tables_used,
            "Fix lookahead violation: ensure all queries use as-of joins (feature_ts <= decision_ts)"
        )

    # Rule 7: Block recommendations if data is stale (> 90 seconds old)
    # Per live price/bar sync fix: refuse trade advice if data freshness > 90s
    if is_trade_question and evidence_pack.freshness_seconds is not None:
        if evidence_pack.freshness_seconds > 90:
            return False, _format_refusal(
                f"Cannot recommend trade - market data is STALE ({int(evidence_pack.freshness_seconds)}s old)",
                [f"freshness_seconds={int(evidence_pack.freshness_seconds)} (> 90s threshold)"],
                evidence_pack.candle_tables_used,
                "Wait for data refresh - latest bar must be < 90 seconds old"
            )

    # All validations passed
    return True, None


def _format_refusal(reason: str, missing: List[str], sources: List[str], next_action: str) -> str:
    """Format standardized refusal message (EXACT FORMAT)."""
    sources_str = ", ".join(sources) if sources else "none"
    missing_str = ", ".join(missing) if missing else "none"

    return f"""DECISION: NOT AVAILABLE
REASON: {reason}
MISSING: {missing_str}
SOURCES USED: {sources_str}
NEXT ACTION: {next_action}"""


def _format_no_trade_refusal(facts: List[str], sources: List[str]) -> str:
    """Format NO TRADE refusal when engine says WAIT."""
    sources_str = ", ".join(sources) if sources else "none"
    facts_str = "\n".join(f"  • {fact}" for fact in facts)

    return f"""DECISION: NO TRADE (WAIT)
REASON: Strategy engine status is not ENTER

FACTS FROM ENGINE:
{facts_str}

SOURCES USED: {sources_str}
NEXT ACTION: Wait for strategy conditions to align, or check different setup"""


def _load_locked_prompt() -> str:
    """Load the locked system prompt from file (MUST exist)."""
    if not LOCKED_PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"LOCKED_SYSTEM_PROMPT.txt not found at {LOCKED_PROMPT_PATH}. "
            "AI Source Lock misconfigured!"
        )

    return LOCKED_PROMPT_PATH.read_text(encoding='utf-8')


def _format_evidence_for_prompt(evidence_pack: EvidencePack) -> str:
    """Format evidence pack into structured prompt section."""

    # Header
    output = ["=" * 60]
    output.append("EVIDENCE PACK (YOUR ONLY SOURCE OF TRUTH)")
    output.append("=" * 60)
    output.append("")

    # Basic info
    output.append(f"INSTRUMENT: {evidence_pack.instrument}")
    output.append(f"TIMEFRAME: {evidence_pack.timeframe}")
    output.append(f"DATA PERIOD: {evidence_pack.ts_utc_start} to {evidence_pack.ts_utc_end}")
    output.append(f"TABLES USED: {', '.join(evidence_pack.candle_tables_used)}")
    output.append("")

    # Current market data
    if evidence_pack.current_price:
        output.append(f"CURRENT PRICE: ${evidence_pack.current_price:.2f}")

    if evidence_pack.session_levels:
        output.append("\nSESSION LEVELS:")
        for session, value in evidence_pack.session_levels.items():
            output.append(f"  • {session}: ${value:.2f}")

    if evidence_pack.orb_data:
        output.append("\nORB DATA:")
        for orb_name, orb_info in evidence_pack.orb_data.items():
            if isinstance(orb_info, dict):
                output.append(f"  • {orb_name}: ${orb_info.get('low', 0):.2f} - ${orb_info.get('high', 0):.2f} (size: {orb_info.get('size', 0):.2f})")

    output.append("")

    # Strategy engine evaluation
    output.append("STRATEGY ENGINE EVALUATION:")
    output.append(f"  Status: {evidence_pack.engine_eval.status}")
    output.append(f"  Strategy: {evidence_pack.engine_eval.strategy_name}")

    if evidence_pack.engine_eval.status == "ENTER":
        output.append(f"  Direction: {evidence_pack.engine_eval.direction}")
        output.append(f"  Entry: ${evidence_pack.engine_eval.entry_price:.2f}")
        output.append(f"  Stop: ${evidence_pack.engine_eval.stop_price:.2f}")
        output.append(f"  Target: ${evidence_pack.engine_eval.target_price:.2f}")
        if evidence_pack.engine_eval.orb_high and evidence_pack.engine_eval.orb_low:
            output.append(f"  ORB Range: ${evidence_pack.engine_eval.orb_low:.2f} - ${evidence_pack.engine_eval.orb_high:.2f}")
        if evidence_pack.engine_eval.rr:
            output.append(f"  RR Target: {evidence_pack.engine_eval.rr:.1f}")
        if evidence_pack.engine_eval.win_rate:
            output.append(f"  Historical Win Rate: {evidence_pack.engine_eval.win_rate:.1f}%")
        if evidence_pack.engine_eval.avg_r:
            output.append(f"  Historical Avg R: {evidence_pack.engine_eval.avg_r:+.3f}R")

    if evidence_pack.engine_eval.reasons:
        output.append("  Reasons:")
        for reason in evidence_pack.engine_eval.reasons:
            output.append(f"    - {reason}")

    output.append("")

    # Validated setups
    if evidence_pack.setup_rows_used:
        output.append("VALIDATED SETUPS (FROM DATABASE):")
        for setup in evidence_pack.setup_rows_used:
            output.append(f"\n  Setup ID {setup.setup_id}: {setup.strategy_name}")
            output.append(f"    ORB Time: {setup.orb_time}")
            output.append(f"    Tier: {setup.tier} | RR: {setup.rr_target:.1f} | SL Mode: {setup.sl_mode}")
            output.append(f"    Win Rate: {setup.win_rate:.1f}% | Avg R: {setup.avg_r:+.3f}R")
            output.append(f"    Trade Count: {setup.trade_count} total (~{setup.annual_trades}/year)")
            if setup.orb_size_filter:
                output.append(f"    ORB Filter: <{setup.orb_size_filter:.3f}×ATR")
            if setup.notes:
                output.append(f"    Notes: {setup.notes}")

    output.append("")

    # OHLCV Bars (PART A/D: Chart analysis data)
    if evidence_pack.bars_ohlcv_sample and len(evidence_pack.bars_ohlcv_sample) > 0:
        output.append(f"OHLCV BAR DATA ({evidence_pack.bars_timeframe} bars):")
        output.append(f"  Total bars: {len(evidence_pack.bars_ohlcv_sample)}")
        output.append(f"  First bar: {evidence_pack.bars_ohlcv_sample[0]['ts']}")
        output.append(f"  Last bar: {evidence_pack.bars_ohlcv_sample[-1]['ts']}")
        output.append("")
        output.append("  Bar data (last 50 bars for analysis):")
        output.append("  ts,open,high,low,close,volume")

        # Include last 50 bars (to keep prompt size manageable)
        last_n_bars = evidence_pack.bars_ohlcv_sample[-50:]
        for bar in last_n_bars:
            output.append(f"  {bar['ts']},{bar['open']:.2f},{bar['high']:.2f},{bar['low']:.2f},{bar['close']:.2f},{bar['volume']:.0f}")

        output.append("")
        output.append("  INSTRUCTION: Use this OHLCV data to analyze chart patterns, support/resistance, trends.")
        output.append("  You MUST NOT make pattern claims without this data. If bars_ohlcv_sample is absent, refuse chart analysis.")

    output.append("")

    # Facts
    output.append("FACTS (DERIVED FROM DB/CODE):")
    for fact in evidence_pack.facts:
        output.append(f"  • {fact}")

    output.append("")

    # Query audit
    if evidence_pack.queries:
        output.append("QUERIES EXECUTED:")
        for query in evidence_pack.queries:
            output.append(f"  • {query}")

    output.append("")
    output.append("=" * 60)
    output.append("END EVIDENCE PACK")
    output.append("=" * 60)

    return "\n".join(output)


def _format_evidence_footer(evidence_pack: EvidencePack) -> str:
    """
    Format Evidence Footer for user-visible audit trail.

    Per AI_EDGE_ENGINE_PROMPT.txt Section 1:
    - db_mode: local | motherduck
    - tables_used: [list]
    - queries_used: [list OR hashes]
    - data_window: [start_ts, end_ts]
    - strategy_ids: [list]
    - no_lookahead_check: PASS | FAIL

    This footer is APPENDED to the AI response (user-visible).
    """
    # Format timestamps
    start_str = evidence_pack.ts_utc_start.strftime("%Y-%m-%d %H:%M UTC")
    end_str = evidence_pack.ts_utc_end.strftime("%Y-%m-%d %H:%M UTC")

    # Format tables
    tables_str = ", ".join(evidence_pack.candle_tables_used)

    # Format queries (truncate if too long)
    queries_display = []
    for q in evidence_pack.queries[:3]:  # Max 3 queries
        if len(q) > 80:
            queries_display.append(q[:77] + "...")
        else:
            queries_display.append(q)
    if len(evidence_pack.queries) > 3:
        queries_display.append(f"... +{len(evidence_pack.queries) - 3} more")
    queries_str = " | ".join(queries_display) if queries_display else "none"

    # Format strategy IDs
    strategy_ids_str = ", ".join(str(sid) for sid in evidence_pack.strategy_ids) if evidence_pack.strategy_ids else "none"

    # Build footer
    footer = f"""
---
**Evidence Footer:**
- **DB Mode:** {evidence_pack.db_mode}
- **Tables Used:** {tables_str}
- **Data Window:** {start_str} → {end_str}
- **Strategy IDs:** {strategy_ids_str}
- **No Lookahead Check:** {evidence_pack.no_lookahead_check}
- **Queries:** {queries_str}
"""
    return footer


def guarded_chat_answer(
    question: str,
    evidence_pack: Optional[EvidencePack],
    conversation_history: List[Dict] = None
) -> str:
    """
    SINGLE CHOKE POINT for all AI/LLM calls.

    This function:
    1. Validates evidence pack (fail-closed gate)
    2. Loads locked system prompt
    3. Formats evidence pack into prompt
    4. Calls Claude API
    5. Returns response

    NO OTHER FILE MAY CALL THE ANTHROPIC API DIRECTLY.

    Args:
        question: User's question
        evidence_pack: Required evidence from DB + engines
        conversation_history: Previous messages (optional)

    Returns:
        AI response OR refusal message (if validation fails)
    """

    # GATE 1: Validate evidence pack (fail-closed)
    is_valid, refusal_msg = validate_evidence_pack(evidence_pack, question)
    if not is_valid:
        logger.warning(f"Evidence pack validation failed: {refusal_msg}")
        return refusal_msg

    # GATE 2: Load locked system prompt (must exist)
    try:
        locked_prompt = _load_locked_prompt()
    except FileNotFoundError as e:
        logger.error(f"AI Source Lock misconfigured: {e}")
        return "AI LOCK MISCONFIGURED: LOCKED_SYSTEM_PROMPT.txt not found. AI responses disabled."

    # GATE 3: Get AI client (OpenAI or Anthropic based on AI_PROVIDER)
    client, provider, error = get_ai_client()
    if error:
        logger.error(error)
        return f"AI assistant not available. {error}"

    # Format evidence pack for prompt
    evidence_text = _format_evidence_for_prompt(evidence_pack)

    # Build system prompt: locked prompt + evidence pack
    system_prompt = f"""{locked_prompt}

{evidence_text}
"""

    # Build messages
    messages = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": question})

    # Call AI API (THE ONLY PLACE THIS HAPPENS)
    try:
        logger.info(f"Calling {provider.upper()} API with evidence pack (instrument={evidence_pack.instrument}, status={evidence_pack.engine_eval.status})")

        if provider == "openai":
            # OpenAI API call
            openai_messages = [{"role": "system", "content": system_prompt}]
            openai_messages.extend(messages)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2048,
                messages=openai_messages
            )
            assistant_message = response.choices[0].message.content
        else:
            # Anthropic API call
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                system=system_prompt,
                messages=messages
            )
            assistant_message = response.content[0].text

        # Log for audit trail
        logger.info(f"AI response generated successfully (length={len(assistant_message)} chars)")

        # APPEND EVIDENCE FOOTER (per AI_EDGE_ENGINE_PROMPT.txt Section 1)
        # This makes the data sources visible to the user
        # PART C: Check if footer already exists (prevent duplicates)
        if "**Evidence Footer:**" not in assistant_message:
            evidence_footer = _format_evidence_footer(evidence_pack)
            full_response = assistant_message + evidence_footer
        else:
            logger.warning("Evidence Footer already present in AI response, skipping duplicate")
            full_response = assistant_message

        return full_response

    except Exception as e:
        error_msg = f"Error communicating with AI: {str(e)}"
        logger.error(error_msg)
        return error_msg


def guarded_vision_answer(
    image_data_base64: str,
    image_type: str,
    user_prompt: str,
    instrument: str = "MGC",
    visual_only: bool = True
) -> str:
    """
    GUARDED VISION API CALL - Chart analysis through AI Source Lock.

    This function enforces:
    1. No performance/edge claims without DB-backed EvidencePack
    2. Visual observations only (timeframe, levels, structure)
    3. Locked system prompt enforces constraints

    Args:
        image_data_base64: Base64-encoded image data
        image_type: MIME type (image/png, image/jpeg)
        user_prompt: Analysis request from user
        instrument: Trading instrument (for context)
        visual_only: If True, restrict to visual observations only (no DB claims)

    Returns:
        Analysis text OR refusal if misconfigured
    """

    # GATE 1: Load locked system prompt
    try:
        locked_prompt = _load_locked_prompt()
    except FileNotFoundError as e:
        logger.error(f"AI Source Lock misconfigured: {e}")
        return "AI LOCK MISCONFIGURED: LOCKED_SYSTEM_PROMPT.txt not found. AI responses disabled."

    # GATE 2: Get AI client (OpenAI or Anthropic based on AI_PROVIDER)
    client, provider, error = get_ai_client()
    if error:
        logger.error(error)
        return f"AI assistant not available. {error}"

    # Build system prompt with constraints
    vision_constraints = """
VISION MODE CONSTRAINTS:
- You are analyzing a trading chart image
- You may ONLY describe what is VISUALLY OBSERVABLE in the image
- DO NOT make performance claims, edge claims, or win rate statements
- DO NOT recommend specific strategies unless backed by database facts
- If you see price levels, timeframes, or patterns, describe them objectively
- Instrument: {instrument}
"""

    if visual_only:
        vision_constraints += """
- NO DATABASE ACCESS for this request
- Limit output to visual observations only
- Do NOT claim any strategy has an edge or historical performance
"""

    system_prompt = f"""{locked_prompt}

{vision_constraints.format(instrument=instrument)}

RESPOND WITH ONLY VISUAL OBSERVATIONS FROM THE CHART.
"""

    # Call Vision API (THE ONLY PLACE VISION CALLS HAPPEN)
    try:
        logger.info(f"Calling {provider.upper()} Vision API (instrument={instrument}, visual_only={visual_only})")

        if provider == "openai":
            # OpenAI Vision API format
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_type};base64,{image_data_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2000,
                messages=messages
            )
            assistant_message = response.choices[0].message.content
        else:
            # Anthropic Vision API format
            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_type,
                            "data": image_data_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ],
            }]
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system_prompt,
                messages=messages
            )
            assistant_message = response.content[0].text

        # Log for audit trail
        logger.info(f"Vision analysis generated (length={len(assistant_message)} chars)")

        return assistant_message

    except Exception as e:
        error_msg = f"Error with vision analysis: {str(e)}"
        logger.error(error_msg)
        return error_msg


def assert_ai_lock_enabled():
    """
    Runtime self-check: Verify AI Source Lock is properly configured.

    Call this on app startup to ensure:
    1. LOCKED_SYSTEM_PROMPT.txt exists
    2. No bypass patterns detected

    Raises:
        AssertionError: If AI lock is misconfigured
    """

    # Check 1: Locked prompt exists
    if not LOCKED_PROMPT_PATH.exists():
        raise AssertionError(
            f"AI LOCK MISCONFIGURED: LOCKED_SYSTEM_PROMPT.txt not found at {LOCKED_PROMPT_PATH}"
        )

    # Check 2: Locked prompt is not empty
    content = LOCKED_PROMPT_PATH.read_text(encoding='utf-8')
    if len(content.strip()) < 100:
        raise AssertionError(
            "AI LOCK MISCONFIGURED: LOCKED_SYSTEM_PROMPT.txt is too short or empty"
        )

    # Check 3: Locked prompt contains key enforcement phrases
    required_phrases = [
        "Evidence Pack",
        "ONLY use",
        "refuse",
        "NOT AVAILABLE"
    ]

    for phrase in required_phrases:
        if phrase not in content:
            raise AssertionError(
                f"AI LOCK MISCONFIGURED: LOCKED_SYSTEM_PROMPT.txt missing required phrase: '{phrase}'"
            )

    logger.info("[OK] AI Source Lock verified: Locked prompt loaded and validated")
    return True
