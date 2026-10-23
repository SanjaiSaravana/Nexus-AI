import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory, MemoryType
from app.services.embedding import embedding_service
from app.core.config import settings

def utcnow():
    return datetime.now(timezone.utc)

TRIVIAL_WORDS = {
    "hi", "hello", "hey", "howdy", "yo", "sup", "there",
    "how", "are", "you", "whats", "up", "good", "morning", "evening", "afternoon", "greetings",
    "thanks", "thank", "a", "lot", "much", "very", "ok", "okay", "cool", "got", "it",
    "awesome", "great", "yes", "yeah", "yep", "no", "nah", "sure", "fine", "bye", "goodbye",
    "sounds", "perfect", "done", "alright"
}

GENERIC_QUESTION_STARTERS = (
    "what is ", "what are ", "who is ", "how do i ", "how does ", "how can i ",
    "explain ", "tell me about ", "can you explain ", "why is ", "where is "
)

class MemoryService:
    def is_conversational_noise(self, text: str) -> bool:
        """Filter out pure greetings, trivial pleasantries, or generic questions without self-statements."""
        cleaned = text.strip().lower()
        cleaned_no_punct = re.sub(r'[^\w\s]', '', cleaned).strip()
        words = cleaned_no_punct.split()

        if not words:
            return True

        # If all words in the message are trivial words (e.g. "Hello there!", "Thanks a lot!")
        if set(words).issubset(TRIVIAL_WORDS):
            return True

        # Check if it's an instructional or general question
        for starter in GENERIC_QUESTION_STARTERS:
            if cleaned.startswith(starter):
                return True

        # Check if it's an impersonal question (no first-person indicators)
        has_first_person = bool(re.search(r'\b(i|my|me|we|our|myself)\b', cleaned))
        if not has_first_person and cleaned.endswith('?'):
            return True

        return False

    def extract_memories(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract meaningful memories from conversation or input text.
        Classifies into Semantic, Episodic, Procedural, or Working memory with importance scoring.
        """
        if self.is_conversational_noise(text):
            return []

        candidates = []
        cleaned = text.strip()

        # Split into sentences or independent clauses
        sentences = [s.strip() for s in re.split(r'[\.\n;]+', cleaned) if s.strip()]

        for sent in sentences:
            s_lower = sent.lower()

            # 1. SEMANTIC MEMORY (Facts about user: skills, knowledge, role, identity)
            # Examples: "I know Python", "I am a backend engineer", "My name is John"
            if re.search(r'\b(i know|i code in|i am proficient in|i use|i work as|i am a|my job is|my role is|my background is)\b', s_lower):
                canonical = self._canonicalize_first_person(sent)
                candidates.append({
                    "content": canonical,
                    "memory_type": MemoryType.SEMANTIC.value,
                    "importance": 0.85,
                    "reason": "User technical skill or professional fact",
                    "entities": self._extract_entities(sent)
                })
                continue

            if re.search(r'\b(i have\s+\d+\+?\s+years|i graduated from|i live in|my company is)\b', s_lower):
                canonical = self._canonicalize_first_person(sent)
                candidates.append({
                    "content": canonical,
                    "memory_type": MemoryType.SEMANTIC.value,
                    "importance": 0.80,
                    "reason": "User biographical or background fact",
                    "entities": self._extract_entities(sent)
                })
                continue

            # 2. EPISODIC MEMORY (Past events, experiences, sessions)
            # Examples: "Yesterday I had an interview", "I previously prepared for a software engineering interview"
            if re.search(r'\b(yesterday|last week|last month|last year|previously|earlier|in \d{4})\b', s_lower) or \
               re.search(r'\b(i previously|i prepared for|i interviewed at|i had an interview|i completed|i passed|i failed)\b', s_lower):
                canonical = self._canonicalize_first_person(sent)
                candidates.append({
                    "content": canonical,
                    "memory_type": MemoryType.EPISODIC.value,
                    "importance": 0.78,
                    "reason": "Past event, experience, or milestone",
                    "entities": self._extract_entities(sent)
                })
                continue

            # 3. PROCEDURAL MEMORY (Preferences, workflows, patterns)
            # Examples: "I prefer dark mode", "Always give me concise Python code", "I like to work in 90-min blocks"
            if re.search(r'\b(i prefer|i always prefer|i like to|always give me|never give me|my workflow is|i usually|format as)\b', s_lower):
                canonical = self._canonicalize_first_person(sent)
                candidates.append({
                    "content": canonical,
                    "memory_type": MemoryType.PROCEDURAL.value,
                    "importance": 0.82,
                    "reason": "User preference or working pattern",
                    "entities": self._extract_entities(sent)
                })
                continue

            # 4. WORKING MEMORY (Current active task / focus)
            # Examples: "Currently working on Phase 3", "I am now debugging database migrations"
            if re.search(r'\b(currently working on|right now i am|today i am focusing on|i am currently|i am now fixing)\b', s_lower):
                canonical = self._canonicalize_first_person(sent)
                candidates.append({
                    "content": canonical,
                    "memory_type": MemoryType.WORKING.value,
                    "importance": 0.65,
                    "reason": "Active conversation or task context",
                    "entities": self._extract_entities(sent)
                })
                continue

        return candidates

    def _canonicalize_first_person(self, sentence: str) -> str:
        """Convert first-person phrasing ('I know Python') into canonical third-person fact ('User knows Python')."""
        s = sentence.strip()
        # Common replacements at start or mid sentence
        replacements = [
            (r'\bI am currently\b', 'User is currently'),
            (r'\bI am\b', 'User is'),
            (r'\bI have been\b', 'User has been'),
            (r'\bI have\b', 'User has'),
            (r'\bI know\b', 'User knows'),
            (r'\bI prefer\b', 'User prefers'),
            (r'\bI code in\b', 'User codes in'),
            (r'\bI work as\b', 'User works as'),
            (r'\bI previously\b', 'User previously'),
            (r'\bI prepared for\b', 'User prepared for'),
            (r'\bI had\b', 'User had'),
            (r'\bI completed\b', 'User completed'),
            (r'\bI like to\b', 'User likes to'),
            (r'\bI usually\b', 'User usually'),
            (r'\bI\b', 'User'),
            (r'\bmy\b', 'user\'s'),
            (r'\bMy\b', 'User\'s'),
            (r'\bme\b', 'user'),
            (r'\bmyself\b', 'the user')
        ]
        canonical = s
        for pat, repl in replacements:
            canonical = re.sub(pat, repl, canonical)

        # Capitalize first letter
        canonical = canonical[0].upper() + canonical[1:] if canonical else ""
        if not canonical.endswith('.'):
            canonical += '.'
        return canonical

    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extractor for technologies, companies, and roles."""
        known_entities = {
            "python", "typescript", "javascript", "go", "golang", "rust", "c++", "java",
            "docker", "kubernetes", "aws", "gcp", "azure", "postgresql", "postgres", "sqlite",
            "redis", "react", "fastapi", "next.js", "vite", "graphql", "tailwind",
            "interview", "system design", "machine learning", "dark mode", "light mode"
        }
        found = []
        lower = text.lower()
        for ent in known_entities:
            if re.search(rf'\b{re.escape(ent)}\b', lower):
                found.append(ent)
        return found

    async def deduplicate_and_store(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        candidate: Dict[str, Any],
        source: str = "conversation",
        source_id: Optional[str] = None
    ) -> Tuple[Memory, bool]:
        """
        Check existing user memories for duplicate or near-identical records.
        If duplicate found (similarity >= 0.85): reinforces/updates existing memory without creating duplicate row.
        If novel: stores new memory with embedding.
        Returns (memory, is_new).
        """
        content = candidate["content"].strip()
        mem_type = candidate.get("memory_type", MemoryType.SEMANTIC.value)
        importance = float(candidate.get("importance", 0.5))
        entities = candidate.get("entities", [])

        # 1. Fetch user's existing memories
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .where(Memory.memory_type == mem_type)
        )
        res = await db.execute(stmt)
        existing_memories = res.scalars().all()

        cand_emb = await embedding_service.get_embedding(content)

        best_match: Optional[Memory] = None
        best_sim = 0.0

        for existing in existing_memories:
            sim = 0.0
            if existing.embedding:
                sim = embedding_service.cosine_similarity(cand_emb, existing.embedding)
            else:
                # Fallback to Jaccard token similarity
                set_cand = set(content.lower().split())
                set_exist = set(existing.content.lower().split())
                if set_cand and set_exist:
                    sim = len(set_cand & set_exist) / len(set_cand | set_exist)

            if sim > best_sim:
                best_sim = sim
                best_match = existing

        # Deduplication Threshold (>= 0.82)
        if best_match and best_sim >= 0.82:
            # Update/reinforce existing memory
            best_match.access_count += 1
            best_match.last_accessed_at = utcnow()
            # Upgrade importance if candidate has higher score
            if importance > best_match.importance:
                best_match.importance = importance
            # Refine content if new detail present
            if len(content) > len(best_match.content):
                best_match.content = content
                best_match.embedding = cand_emb

            metadata = dict(best_match.mem_metadata or {})
            existing_entities = set(metadata.get("entities", []))
            existing_entities.update(entities)
            metadata["entities"] = list(existing_entities)
            best_match.mem_metadata = metadata
            best_match.updated_at = utcnow()

            await db.commit()
            await db.refresh(best_match)
            return best_match, False

        # Otherwise: store novel memory
        new_memory = Memory(
            user_id=user_id,
            memory_type=mem_type,
            content=content,
            importance=importance,
            source=source,
            source_id=source_id,
            mem_metadata={"entities": entities, "reason": candidate.get("reason", "Extracted fact")},
            embedding=cand_emb,
            access_count=1,
            last_accessed_at=utcnow(),
            created_at=utcnow(),
            updated_at=utcnow()
        )
        db.add(new_memory)
        await db.commit()
        await db.refresh(new_memory)
        return new_memory, True

    async def retrieve_memories(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        memory_types: Optional[List[str]] = None,
        top_k: int = 5,
        min_importance: float = 0.3
    ) -> List[Tuple[Memory, float]]:
        """
        Retrieve relevant memories for a user query.
        Combines semantic similarity (70%) and importance score (30%).
        Strictly enforces user_id isolation.
        """
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .where(Memory.importance >= min_importance)
        )
        if memory_types:
            stmt = stmt.where(Memory.memory_type.in_(memory_types))

        res = await db.execute(stmt)
        memories = res.scalars().all()

        if not memories:
            return []

        query_emb = await embedding_service.get_embedding(query)
        query_words = set(re.findall(r'\b\w+\b', query.lower())) - TRIVIAL_WORDS
        scored: List[Tuple[Memory, float]] = []

        for mem in memories:
            sim = 0.0
            if mem.embedding:
                sim = embedding_service.cosine_similarity(query_emb, mem.embedding)
            else:
                set_q = set(query.lower().split())
                set_m = set(mem.content.lower().split())
                if set_q and set_m:
                    sim = len(set_q & set_m) / len(set_q | set_m)

            # Lexical entity & keyword overlap
            mem_words = set(re.findall(r'\b\w+\b', mem.content.lower()))
            metadata = mem.mem_metadata or {}
            entities = set(metadata.get("entities", []))
            overlap = len(query_words & (mem_words | entities))
            lex_score = min(1.0, overlap * 0.35)

            # Composite score: 45% dense similarity + 35% lexical overlap + 20% importance
            composite_score = (sim * 0.45) + (lex_score * 0.35) + (mem.importance * 0.20)
            scored.append((mem, composite_score))

        # Sort descending by composite score
        scored.sort(key=lambda x: x[1], reverse=True)
        top_results = scored[:top_k]

        # Update access count & last_accessed_at
        now = utcnow()
        for mem, _ in top_results:
            mem.access_count += 1
            mem.last_accessed_at = now

        await db.commit()
        return top_results

    async def process_conversation_message(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        message: str,
        conversation_id: Optional[uuid.UUID] = None
    ) -> List[Memory]:
        """Orchestrate extraction, scoring, deduplication, and persistence from a conversation message."""
        candidates = self.extract_memories(message)
        saved = []
        for cand in candidates:
            if cand.get("importance", 0.0) >= 0.40:
                mem, _ = await self.deduplicate_and_store(
                    db,
                    user_id=user_id,
                    candidate=cand,
                    source="conversation",
                    source_id=str(conversation_id) if conversation_id else None
                )
                saved.append(mem)
        return saved

memory_service = MemoryService()
