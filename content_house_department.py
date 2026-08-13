import os
import sys
from typing import Optional, List, Any

# Configure UTF-8 encoding for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

# Pydantic V1 type inference patch for ChromaDB under Python 3.14
try:
    import pydantic.v1.fields
    _orig_set_default = pydantic.v1.fields.ModelField._set_default_and_type
    def _safe_set_default(self):
        if getattr(self, 'type_', None) is None or self.type_ is pydantic.v1.fields.Undefined:
            if hasattr(self, 'default') and self.default is not None and self.default is not pydantic.v1.fields.Undefined:
                self.type_ = type(self.default)
                self.outer_type_ = self.type_
            else:
                self.type_ = str
                self.outer_type_ = str
        return _orig_set_default(self)
    pydantic.v1.fields.ModelField._set_default_and_type = _safe_set_default
except Exception:
    pass

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

from pydantic import BaseModel, Field
from crewai import Agent, LLM
from crewai.tools import tool
from crewai_tools import DirectoryReadTool
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

from finance_department import get_resilient_llm
from custom_tools import live_web_search


# =====================================================================
# Step 1: Define Omnichannel Guardrails (Structured Output)
# =====================================================================
class OmnichannelDeliverable(BaseModel):
    """
    Structured Guardrail Model for Omnichannel Content Studio deliverables.
    Enforces comprehensive multi-format assets across written copy, video scripts,
    B-roll cinematography directions, and thumbnail/banner generative prompts.
    """
    written_post: str = Field(
        ...,
        description="A complete, high-engagement written post tailored for LinkedIn, Twitter/X, and corporate blog or newsletter publishing."
    )
    video_script: str = Field(
        ...,
        description="Full video script containing exact spoken dialogue/voiceover, speaker pacing markers, and text-on-screen (TOS) graphics cues."
    )
    b_roll_instructions: str = Field(
        ...,
        description="Cinematic B-roll visual directions, camera angles, transitions, and stock footage cues mapped directly to the script timeline."
    )
    image_generation_prompt: str = Field(
        ...,
        description="A highly detailed, production-grade text-to-image prompt (Midjourney/DALL-E 3) describing lighting, subject composition, artistic style, camera lens, and aspect ratio for banners or thumbnails."
    )


# Backward compatibility alias
ContentDeliverable = OmnichannelDeliverable


# =====================================================================
# Step 2: Define Trend Analysis & YouTube Hook Tools
# =====================================================================
@tool("RSS Trend Scraper")
def rss_trend_scraper(feed_url: str) -> str:
    """
    Fetches and parses an RSS or Atom feed URL to extract current trending topics, headlines, and articles.
    Extracts the titles and summaries of the top 5 most recent entries.

    Args:
        feed_url: The URL of the RSS or Atom feed to fetch and parse.
    """
    if feedparser is None:
        return f"Notice: feedparser library is not available. Unable to parse RSS feed from '{feed_url}'."

    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return f"No entries found for RSS feed at: '{feed_url}'"

        formatted_entries = []
        for i, entry in enumerate(feed.entries[:5], 1):
            title = entry.get("title", "No Title")
            summary = entry.get("summary", entry.get("description", "No Summary"))
            link = entry.get("link", "")
            clean_summary = summary.replace("<p>", "").replace("</p>", "").replace("<br>", " ").replace("<b>", "").replace("</b>", "").strip()
            formatted_entries.append(f"{i}. Title: {title}\n   Summary: {clean_summary}\n   Link: {link}")

        feed_title = feed.feed.get("title", feed_url)
        return f"=== Trending Topics from '{feed_title}' ===\n\n" + "\n\n".join(formatted_entries)
    except Exception as e:
        return f"Error parsing RSS feed from '{feed_url}': {e}"


@tool("YouTube Hook Analyzer")
def youtube_hook_analyzer(video_id: str) -> str:
    """
    Fetches the transcript for a specified YouTube video ID and extracts the text from the first 60 seconds
    (or roughly the first 150 words) to isolate and reverse-engineer the video's viral opening hook and pacing.

    Args:
        video_id: The YouTube Video ID (e.g. 'dQw4w9WgXcQ') or full YouTube URL to extract the opening hook from.
    """
    if YouTubeTranscriptApi is None:
        return f"Notice: youtube-transcript-api library is not available. Unable to fetch transcript for '{video_id}'."

    try:
        clean_id = video_id.strip()
        if "watch?v=" in clean_id:
            clean_id = clean_id.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in clean_id:
            clean_id = clean_id.split("youtu.be/")[1].split("?")[0]

        transcript_list = YouTubeTranscriptApi.get_transcript(clean_id)
        if not transcript_list:
            return f"No transcript available for YouTube video: '{clean_id}'"

        hook_segments = []
        total_words = 0

        for item in transcript_list:
            start_time = item.get("start", 0)
            text = item.get("text", "").strip()
            if not text:
                continue

            hook_segments.append(text)
            total_words += len(text.split())

            if start_time >= 60.0 or total_words >= 150:
                break

        opening_hook_text = " ".join(hook_segments)
        return (
            f"=== YouTube Opening Hook (First 60s / ~150 words) [Video ID: {clean_id}] ===\n\n"
            f"{opening_hook_text}\n\n"
            f"[Word Count: ~{total_words} words]"
        )
    except Exception as e:
        return f"Error extracting YouTube transcript hook for '{video_id}': {e}"


# =====================================================================
# Step 3: 5-Agent Omnichannel Studio Definitions
# =====================================================================
class ContentHouseDepartment:
    """
    Enterprise Omnichannel Content Production Studio Ecosystem.
    Instantiates specialized media production agents equipped with RSS trend scraping,
    YouTube transcript hook analysis, live web research intelligence, central knowledge base RAG tool,
    and bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: Optional[LLM] = None, knowledge_tool: Any = None):
        self.llm = llm if llm is not None else get_resilient_llm()
        self.knowledge_tool = knowledge_tool if knowledge_tool is not None else DirectoryReadTool(directory="company_knowledge_base")

    def create_creative_director(self) -> Agent:
        """1. Creative Director: Analyzes trending topics, dictates narrative arc, visual style, and tone for the piece."""
        tools = (
            [rss_trend_scraper, youtube_hook_analyzer, self.knowledge_tool, live_web_search]
            if self.knowledge_tool
            else [rss_trend_scraper, youtube_hook_analyzer, live_web_search]
        )
        return Agent(
            role="Creative Director",
            goal=(
                "Analyze trending topics, audience psychology, and market dynamics to architect the overarching "
                "narrative arc, tone, thematic vision, and omnichannel distribution strategy. "
                "You MUST use the rss_trend_scraper to identify current industry narratives, and you MUST use the "
                "youtube_hook_analyzer on at least one successful reference video to reverse-engineer its pacing BEFORE briefing the Scriptwriter."
            ),
            backstory=(
                "You are an acclaimed digital Creative Director who has architected viral media campaigns and top-tier creator channels. "
                "You conduct deep market research using live web intelligence, RSS trend feeds, and video hook reverse-engineering. "
                "You MUST use the rss_trend_scraper to identify current industry narratives, and you MUST use the "
                "youtube_hook_analyzer on at least one successful reference video to reverse-engineer its pacing BEFORE briefing the Scriptwriter."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_scriptwriter(self) -> Agent:
        """2. Scriptwriter: Writes deeply engaging, high-retention video scripts and written long-form / social posts."""
        tools = [self.knowledge_tool, live_web_search] if self.knowledge_tool else [live_web_search]
        return Agent(
            role="Scriptwriter",
            goal=(
                "Transform the Creative Director's strategic brief into comprehensive, highly engaging video scripts "
                "and authoritative written articles/posts for LinkedIn, Twitter/X, and blogs."
            ),
            backstory=(
                "You are an elite Scriptwriter and narrative specialist. You excel at turning complex topics "
                "into captivating, bingeable video scripts and high-value written posts. "
                "You master narrative pacing, open loops, relatable storytelling, and clear value delivery."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_long_form_scriptwriter(self) -> Agent:
        """Backwards compatibility alias for Scriptwriter."""
        return self.create_scriptwriter()

    def create_hook_specialist(self) -> Agent:
        """3. Hook Specialist: Crafts high-retention opening hooks, pattern interrupts, and viral framing."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Hook Specialist",
            goal=(
                "Engineer ultra-high-converting short-form viral hooks, pattern interrupts, and curiosity gaps "
                "for the first 3 seconds of video and the opening lines of written content."
            ),
            backstory=(
                "You are a viral growth engineer and Hook Specialist. You understand the science of short-form retention "
                "where the first 3 seconds determine success. You formulate irresistible hooks, visual pattern interrupts, "
                "and psychological curiosity triggers."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_short_form_hook_specialist(self) -> Agent:
        """Backwards compatibility alias for Hook Specialist."""
        return self.create_hook_specialist()

    def create_graphic_designer(self) -> Agent:
        """4. Graphic Designer: Crafts precise, photorealistic Midjourney/DALL-E image generation prompts for banners & thumbnails."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Graphic Designer",
            goal=(
                "Craft highly detailed, production-grade text-to-image prompts (Midjourney/DALL-E 3) "
                "for click-optimized YouTube thumbnails, blog headers, and social media banners based on the content narrative."
            ),
            backstory=(
                "You are an expert AI Visual Artist & Graphic Designer specialized in visual storytelling, color theory, "
                "contrast framing, lighting aesthetics, photorealistic rendering parameters, and high-CTR thumbnail psychology."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_video_producer(self) -> Agent:
        """5. Video Producer: Structures the complete video script, exact B-roll cues, text-on-screen directives, and enforces OmnichannelDeliverable."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Video Producer",
            goal=(
                "Synthesize all assets into a complete production package with precise video dialogue, text-on-screen cues, "
                "cinematic B-roll instructions, and format the final output strictly conforming to the OmnichannelDeliverable schema."
            ),
            backstory=(
                "You are an elite Video Producer & Post-Production Director. You assemble scripts, visual B-roll cues, "
                "audio markers, image generation prompts, and written copy into a master production package conforming strictly to the "
                "OmnichannelDeliverable Pydantic schema."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def get_content_team(self) -> List[Agent]:
        """Returns the complete 5-agent omnichannel production studio workflow team."""
        return [
            self.create_creative_director(),
            self.create_scriptwriter(),
            self.create_hook_specialist(),
            self.create_graphic_designer(),
            self.create_video_producer()
        ]


def get_content_team(llm: Optional[LLM] = None, knowledge_tool: Any = None) -> List[Agent]:
    """
    Module-level factory function returning the 5-agent Omnichannel Content House Studio Team:
    1. Creative Director (Equipped with RSS Trend Scraper and YouTube Hook Analyzer)
    2. Scriptwriter (Long-form and written content)
    3. Hook Specialist (Short-form viral framing)
    4. Graphic Designer (Banners/thumbnails image generation prompt)
    5. Video Producer (Video script, B-roll cues, and master deliverable synthesis)
    """
    dept = ContentHouseDepartment(llm=llm, knowledge_tool=knowledge_tool)
    return dept.get_content_team()


__all__ = [
    "rss_trend_scraper",
    "youtube_hook_analyzer",
    "OmnichannelDeliverable",
    "ContentDeliverable",
    "ContentHouseDepartment",
    "get_content_team",
]
