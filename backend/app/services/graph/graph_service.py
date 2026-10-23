import re
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task
from app.models.goal import Goal
from app.models.document import Document
from app.models.user import User

from app.schemas.knowledge_graph import (
    GraphNode,
    GraphEdge,
    GraphData,
    GraphQueryResponse,
    ExtractedEntity,
    ExtractedRelationship
)
from app.services.graph.neo4j_client import neo4j_client
from app.services.graph.extractor import graph_extractor, TECH_ALIASES, SKILL_ALIASES

logger = logging.getLogger("nexus.knowledge_graph")

class KnowledgeGraphService:
    """Core Knowledge Graph orchestration service for Nexus AI."""

    async def ingest_document_entities(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        filename: str,
        text: str,
        user_name: str = "User"
    ) -> Dict[str, int]:
        """Extract entities and relationships from document text and persist to Neo4j graph."""
        user_id_str = str(user_id)

        # 1. Ensure user node exists
        user_node = await neo4j_client.add_node(
            user_id=user_id_str,
            label="User",
            name=user_name,
            properties={"system_user_id": user_id_str}
        )

        # 2. Add Document node
        doc_node = await neo4j_client.add_node(
            user_id=user_id_str,
            label="Document",
            name=filename,
            properties={"document_id": str(document_id), "source": "upload"}
        )

        # USER -> OWNS -> DOCUMENT
        await neo4j_client.add_edge(
            user_id=user_id_str,
            source_id=user_node["id"],
            target_id=doc_node["id"],
            rel_type="OWNS"
        )

        # 3. Extract entities and relationships
        entities, relationships = graph_extractor.extract_entities_and_relationships(
            text=text,
            user_name=user_name,
            document_name=filename
        )

        # Map: (label, normalized_name) -> node_id
        node_id_map: Dict[Tuple[str, str], str] = {
            ("User", user_node["normalized_name"]): user_node["id"],
            ("Document", doc_node["normalized_name"]): doc_node["id"]
        }

        # 4. Insert / merge entities
        for ent in entities:
            if ent.label == "User":
                continue
            node = await neo4j_client.add_node(
                user_id=user_id_str,
                label=ent.label,
                name=ent.name,
                properties=ent.properties
            )
            node_id_map[(ent.label, ent.normalized_name)] = node["id"]

        # 5. Insert / merge relationships
        created_edges_count = 0
        for rel in relationships:
            src_norm = graph_extractor.normalize_entity_name(rel.source_name, rel.source_label)[1]
            tgt_norm = graph_extractor.normalize_entity_name(rel.target_name, rel.target_label)[1]

            src_id = node_id_map.get((rel.source_label, src_norm))
            tgt_id = node_id_map.get((rel.target_label, tgt_norm))

            if src_id and tgt_id:
                edge = await neo4j_client.add_edge(
                    user_id=user_id_str,
                    source_id=src_id,
                    target_id=tgt_id,
                    rel_type=rel.relationship_type,
                    properties=rel.properties
                )
                if edge:
                    created_edges_count += 1

        return {
            "entities_created": len(entities),
            "relationships_created": created_edges_count
        }

    async def sync_user_database(self, user_id: uuid.UUID, db: AsyncSession) -> Dict[str, int]:
        """Sync relational database entities (Projects, Tasks, Goals, Documents) to Knowledge Graph."""
        user_id_str = str(user_id)

        # 1. User
        user_res = await db.execute(select(User).where(User.id == user_id))
        user_obj = user_res.scalar_one_or_none()
        user_name = user_obj.profile.full_name if (user_obj and user_obj.profile and user_obj.profile.full_name) else (user_obj.username if user_obj else "User")

        user_node = await neo4j_client.add_node(
            user_id=user_id_str,
            label="User",
            name=user_name,
            properties={"system_user_id": user_id_str, "email": user_obj.email if user_obj else ""}
        )

        nodes_count = 1
        edges_count = 0

        # 2. Projects
        p_res = await db.execute(select(Project).where(Project.user_id == user_id))
        projects = p_res.scalars().all()
        project_node_map = {}

        for p in projects:
            p_node = await neo4j_client.add_node(
                user_id=user_id_str,
                label="Project",
                name=p.name,
                properties={
                    "db_id": str(p.id),
                    "status": p.status,
                    "description": p.description or ""
                }
            )
            nodes_count += 1
            project_node_map[p.id] = p_node["id"]

            # USER -> OWNS -> PROJECT
            e = await neo4j_client.add_edge(
                user_id=user_id_str,
                source_id=user_node["id"],
                target_id=p_node["id"],
                rel_type="OWNS"
            )
            if e:
                edges_count += 1

            # Extract any inline technologies from description
            if p.description:
                for tech_alias, canonical_tech in TECH_ALIASES.items():
                    if re.search(rf'\b{re.escape(tech_alias)}\b', p.description.lower()):
                        t_node = await neo4j_client.add_node(
                            user_id=user_id_str,
                            label="Technology",
                            name=canonical_tech
                        )
                        nodes_count += 1
                        edge = await neo4j_client.add_edge(
                            user_id=user_id_str,
                            source_id=p_node["id"],
                            target_id=t_node["id"],
                            rel_type="USES"
                        )
                        if edge:
                            edges_count += 1

        # 3. Goals
        g_res = await db.execute(select(Goal).where(Goal.user_id == user_id))
        goals = g_res.scalars().all()
        goal_node_map = {}

        for g in goals:
            g_node = await neo4j_client.add_node(
                user_id=user_id_str,
                label="Goal",
                name=g.title,
                properties={
                    "db_id": str(g.id),
                    "category": g.category,
                    "status": g.status,
                    "progress_pct": g.progress_pct
                }
            )
            nodes_count += 1
            goal_node_map[g.id] = g_node["id"]

            # USER -> HAS_GOAL -> GOAL
            e = await neo4j_client.add_edge(
                user_id=user_id_str,
                source_id=user_node["id"],
                target_id=g_node["id"],
                rel_type="HAS_GOAL"
            )
            if e:
                edges_count += 1

        # 4. Tasks
        t_res = await db.execute(select(Task).where(Task.user_id == user_id))
        tasks = t_res.scalars().all()

        for t in tasks:
            t_node = await neo4j_client.add_node(
                user_id=user_id_str,
                label="Task",
                name=t.title,
                properties={
                    "db_id": str(t.id),
                    "status": t.status,
                    "priority": t.priority
                }
            )
            nodes_count += 1

            # PROJECT -> HAS_TASK -> TASK
            if t.project_id and t.project_id in project_node_map:
                e1 = await neo4j_client.add_edge(
                    user_id=user_id_str,
                    source_id=project_node_map[t.project_id],
                    target_id=t_node["id"],
                    rel_type="HAS_TASK"
                )
                if e1:
                    edges_count += 1

            # Match Task to any Goal if task title/description supports goal
            for g in goals:
                if (g.title.lower() in t.title.lower()) or (t.description and g.title.lower() in t.description.lower()):
                    if g.id in goal_node_map:
                        e2 = await neo4j_client.add_edge(
                            user_id=user_id_str,
                            source_id=t_node["id"],
                            target_id=goal_node_map[g.id],
                            rel_type="SUPPORTS"
                        )
                        if e2:
                            edges_count += 1

        # 5. Documents
        d_res = await db.execute(select(Document).where(Document.user_id == user_id))
        docs = d_res.scalars().all()

        for d in docs:
            d_node = await neo4j_client.add_node(
                user_id=user_id_str,
                label="Document",
                name=d.filename,
                properties={"db_id": str(d.id), "document_type": d.document_type}
            )
            nodes_count += 1

            # USER -> OWNS -> DOCUMENT
            e = await neo4j_client.add_edge(
                user_id=user_id_str,
                source_id=user_node["id"],
                target_id=d_node["id"],
                rel_type="OWNS"
            )
            if e:
                edges_count += 1

        return {"synced_nodes": nodes_count, "synced_edges": edges_count}

    async def query_graph(self, user_id: uuid.UUID, query: str) -> GraphQueryResponse:
        """Resolve natural language graph query and execute parameterized Cypher."""
        user_id_str = str(user_id)
        q_lower = query.lower().strip()

        # 1. "What projects do I have that use <Tech>?"
        tech_match = re.search(r'(?:projects?.*(?:use|uses|using|built with|with)|what.*projects?.*use)\s+([A-Za-z0-9#+.\s]+)', q_lower)
        if not tech_match:
            # Check for direct queries like "projects that use python" or "projects using python"
            tech_match = re.search(r'projects?.*(?:use|uses|using)\s+([A-Za-z0-9#+.\s]+)', q_lower)

        if tech_match or ("project" in q_lower and any(t in q_lower for t in TECH_ALIASES)):
            target_tech = ""
            if tech_match:
                raw_cand = tech_match.group(1).replace("?", "").replace(".", "").strip()
                target_tech = TECH_ALIASES.get(raw_cand.lower(), raw_cand)
            if not target_tech:
                for alias, canon in TECH_ALIASES.items():
                    if alias in q_lower:
                        target_tech = canon
                        break

            cypher = (
                "MATCH (p:Project {user_id: $user_id})-[:USES]->(t:Technology) "
                "WHERE toLower(t.name) CONTAINS toLower($tech_name) "
                "RETURN p, t"
            )
            params = {"user_id": user_id_str, "tech_name": target_tech}
            records = await neo4j_client.execute_cypher(cypher, params)

            proj_names = sorted(list({r["project"] for r in records if "project" in r}))
            matched_nodes = []
            matched_edges = []
            seen_n = set()

            for r in records:
                p_node = r.get("p")
                t_node = r.get("t")
                r_edge = r.get("r")
                if p_node and p_node["id"] not in seen_n:
                    seen_n.add(p_node["id"])
                    matched_nodes.append(GraphNode(id=p_node["id"], label=p_node["label"], name=p_node["name"], properties=p_node.get("properties", {})))
                if t_node and t_node["id"] not in seen_n:
                    seen_n.add(t_node["id"])
                    matched_nodes.append(GraphNode(id=t_node["id"], label=t_node["label"], name=t_node["name"], properties=t_node.get("properties", {})))
                if r_edge:
                    matched_edges.append(GraphEdge(id=r_edge["id"], source=r_edge["source"], target=r_edge["target"], type=r_edge["type"], properties=r_edge.get("properties", {})))

            if proj_names:
                answer = f"You have {len(proj_names)} project(s) that use {target_tech}: {', '.join(proj_names)}."
            else:
                answer = f"No projects were found in your knowledge graph that use {target_tech}."

            return GraphQueryResponse(
                query=query,
                intent="projects_using_technology",
                cypher=cypher,
                answer=answer,
                nodes=matched_nodes,
                edges=matched_edges
            )

        # 2. "What skills do I know / have?"
        if any(w in q_lower for w in ["skills do i", "my skills", "what skills", "skills i know", "knows"]):
            cypher = "MATCH (u:User {id: $user_id})-[:KNOWS]->(s:Skill) RETURN s"
            params = {"user_id": user_id_str}
            records = await neo4j_client.execute_cypher(cypher, params)
            skills = sorted(list({r.get("skill") or r.get("name") for r in records if r.get("skill") or r.get("name")}))

            matched_nodes = [
                GraphNode(id=r["s"]["id"], label=r["s"]["label"], name=r["s"]["name"], properties=r["s"].get("properties", {}))
                for r in records if "s" in r
            ]

            if skills:
                answer = f"You know {len(skills)} skill(s): {', '.join(skills)}."
            else:
                answer = "No skills found in your knowledge graph."

            return GraphQueryResponse(
                query=query,
                intent="user_skills",
                cypher=cypher,
                answer=answer,
                nodes=matched_nodes,
                edges=[]
            )

        # 3. "What tasks support my goals?"
        if "task" in q_lower and "goal" in q_lower and "support" in q_lower:
            cypher = "MATCH (t:Task {user_id: $user_id})-[:SUPPORTS]->(g:Goal {user_id: $user_id}) RETURN t, g"
            params = {"user_id": user_id_str}
            records = await neo4j_client.execute_cypher(cypher, params)

            matched_nodes = []
            seen_n = set()
            lines = []
            for r in records:
                t = r.get("t")
                g = r.get("g")
                if t and g:
                    lines.append(f"Task '{t['name']}' supports Goal '{g['name']}'")
                    if t["id"] not in seen_n:
                        seen_n.add(t["id"])
                        matched_nodes.append(GraphNode(id=t["id"], label=t["label"], name=t["name"], properties=t.get("properties", {})))
                    if g["id"] not in seen_n:
                        seen_n.add(g["id"])
                        matched_nodes.append(GraphNode(id=g["id"], label=g["label"], name=g["name"], properties=g.get("properties", {})))

            answer = "Tasks supporting your goals:\n" + "\n".join(f"• {l}" for l in lines) if lines else "No task-to-goal support links found in your knowledge graph."

            return GraphQueryResponse(
                query=query,
                intent="tasks_supporting_goals",
                cypher=cypher,
                answer=answer,
                nodes=matched_nodes,
                edges=[]
            )

        # 4. "What jobs require <Skill>?"
        if "job" in q_lower and "require" in q_lower:
            skill_filter = ""
            for alias, canon in SKILL_ALIASES.items():
                if alias in q_lower:
                    skill_filter = canon
                    break

            cypher = "MATCH (j:Job {user_id: $user_id})-[:REQUIRES]->(s:Skill) WHERE toLower(s.name) CONTAINS toLower($skill_name) RETURN j, s"
            params = {"user_id": user_id_str, "skill_name": skill_filter}
            records = await neo4j_client.execute_cypher(cypher, params)

            job_names = sorted(list({r["job"] for r in records if "job" in r}))
            answer = f"Jobs requiring {skill_filter or 'the specified skill'}: {', '.join(job_names)}." if job_names else f"No jobs requiring {skill_filter or 'this skill'} found."

            matched_nodes = []
            seen = set()
            for r in records:
                for k in ["j", "s"]:
                    if k in r and r[k]["id"] not in seen:
                        seen.add(r[k]["id"])
                        matched_nodes.append(GraphNode(id=r[k]["id"], label=r[k]["label"], name=r[k]["name"], properties=r[k].get("properties", {})))

            return GraphQueryResponse(
                query=query,
                intent="jobs_requiring_skill",
                cypher=cypher,
                answer=answer,
                nodes=matched_nodes,
                edges=[]
            )

        # 5. Default Semantic Entity Retrieval
        cypher = "MATCH (n {user_id: $user_id}) RETURN n"
        params = {"user_id": user_id_str}
        raw_nodes = await neo4j_client.get_nodes(user_id=user_id_str, search=query, limit=50)
        edges = await neo4j_client.get_edges(user_id=user_id_str, limit=50)

        nodes = [GraphNode(id=n["id"], label=n["label"], name=n["name"], properties=n.get("properties", {})) for n in raw_nodes]
        graph_edges = [GraphEdge(id=e["id"], source=e["source"], target=e["target"], type=e["type"], properties=e.get("properties", {})) for e in edges]

        answer = f"Found {len(nodes)} related entity node(s) in your knowledge graph matching '{query}'."

        return GraphQueryResponse(
            query=query,
            intent="general_subgraph_search",
            cypher=cypher,
            answer=answer,
            nodes=nodes,
            edges=graph_edges
        )

    async def get_rag_context(self, user_id: uuid.UUID, query: str) -> str:
        """Construct hybrid relational Knowledge Graph context block for LLM prompts."""
        user_id_str = str(user_id)
        q_lower = query.lower()

        # Find relevant nodes matching terms
        user_nodes = await neo4j_client.get_nodes(user_id=user_id_str, limit=100)
        user_edges = await neo4j_client.get_edges(user_id=user_id_str, limit=200)

        node_map = {n["id"]: n for n in user_nodes}

        # Check terms in query using exact word boundaries
        relevant_edges = []
        for e in user_edges:
            src = node_map.get(e["source"])
            tgt = node_map.get(e["target"])
            if not src or not tgt:
                continue
            
            # Avoid matching User or Document labels as accidental query substrings
            src_name = src["name"].strip()
            tgt_name = tgt["name"].strip()
            
            src_match = False
            if src["label"] not in ("User", "Document") and len(src_name) >= 2:
                src_match = bool(re.search(rf'\b{re.escape(src_name.lower())}\b', q_lower))

            tgt_match = False
            if tgt["label"] not in ("User", "Document") and len(tgt_name) >= 2:
                tgt_match = bool(re.search(rf'\b{re.escape(tgt_name.lower())}\b', q_lower))

            if src_match or tgt_match:
                relevant_edges.append((src, e["type"], tgt))

        if not relevant_edges:
            # Check if query specifically mentions a known technology using word boundaries
            for tech_alias, canon_tech in TECH_ALIASES.items():
                if len(tech_alias) >= 2 and re.search(rf'\b{re.escape(tech_alias)}\b', q_lower):
                    for e in user_edges:
                        if e["type"] == "USES":
                            src = node_map.get(e["source"])
                            tgt = node_map.get(e["target"])
                            if src and tgt and tgt["name"].lower() == canon_tech.lower():
                                relevant_edges.append((src, "USES", tgt))

        if not relevant_edges:
            return ""

        facts = []
        for src, rel, tgt in relevant_edges[:10]:
            if rel == "USES":
                facts.append(f"Project '{src['name']}' uses technology '{tgt['name']}'")
            elif rel == "OWNS":
                facts.append(f"User '{src['name']}' owns project '{tgt['name']}'")
            elif rel == "KNOWS":
                facts.append(f"User '{src['name']}' knows skill '{tgt['name']}'")
            elif rel == "REQUIRES":
                facts.append(f"Job '{src['name']}' requires skill '{tgt['name']}'")
            elif rel == "DESCRIBES":
                facts.append(f"Document '{src['name']}' describes project '{tgt['name']}'")
            elif rel == "SUPPORTS":
                facts.append(f"Task '{src['name']}' supports goal '{tgt['name']}'")
            elif rel == "RELATES_TO":
                facts.append(f"Event '{src['name']}' relates to project '{tgt['name']}'")
            else:
                facts.append(f"{src['label']} '{src['name']}' {rel} {tgt['label']} '{tgt['name']}'")

        unique_facts = list(dict.fromkeys(facts))
        return "Knowledge Graph Relationships:\n" + "\n".join(f"• {f}" for f in unique_facts)

    async def get_user_graph_data(
        self,
        user_id: uuid.UUID,
        label: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 300
    ) -> GraphData:
        """Fetch filtered graph data for interactive visualization."""
        user_id_str = str(user_id)
        raw_nodes = await neo4j_client.get_nodes(user_id=user_id_str, label=label, search=search, limit=limit)
        node_ids = {n["id"] for n in raw_nodes}

        raw_edges = await neo4j_client.get_edges(user_id=user_id_str, limit=500)
        filtered_edges = [
            e for e in raw_edges
            if e["source"] in node_ids and e["target"] in node_ids
        ]

        nodes = [
            GraphNode(id=n["id"], label=n["label"], name=n["name"], properties=n.get("properties", {}))
            for n in raw_nodes
        ]
        edges = [
            GraphEdge(id=e["id"], source=e["source"], target=e["target"], type=e["type"], properties=e.get("properties", {}))
            for e in filtered_edges
        ]
        return GraphData(nodes=nodes, edges=edges)

graph_service = KnowledgeGraphService()
