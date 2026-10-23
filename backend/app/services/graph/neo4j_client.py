import uuid
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

from app.core.config import settings

logger = logging.getLogger("nexus.knowledge_graph")

def utcnow():
    return datetime.now(timezone.utc).isoformat()

class InMemoryGraphStore:
    """High-performance in-memory graph repository providing user-isolated Cypher/Graph operations."""

    def __init__(self):
        # node_id -> {id, user_id, label, name, normalized_name, properties, created_at, updated_at}
        self.nodes: Dict[str, Dict[str, Any]] = {}
        # (user_id, label, normalized_name) -> node_id (Strict deduplication index)
        self.node_lookup: Dict[Tuple[str, str, str], str] = {}
        # edge_id -> {id, user_id, source, target, type, properties, created_at, updated_at}
        self.edges: Dict[str, Dict[str, Any]] = {}
        # (user_id, source_id, target_id, type) -> edge_id (Strict edge deduplication index)
        self.edge_lookup: Dict[Tuple[str, str, str, str], str] = {}

    def add_node(
        self,
        user_id: str,
        label: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add or merge a node strictly scoped to user_id to prevent duplicates."""
        user_id_str = str(user_id)
        norm_key = name.strip().lower()
        lookup_key = (user_id_str, label, norm_key)

        if lookup_key in self.node_lookup:
            existing_id = self.node_lookup[lookup_key]
            existing_node = self.nodes[existing_id]
            if properties:
                existing_node["properties"].update(properties)
            existing_node["name"] = name.strip()
            existing_node["updated_at"] = utcnow()
            return existing_node

        n_id = node_id or str(uuid.uuid4())
        new_node = {
            "id": n_id,
            "user_id": user_id_str,
            "label": label,
            "name": name.strip(),
            "normalized_name": norm_key,
            "properties": properties or {},
            "created_at": utcnow(),
            "updated_at": utcnow()
        }
        self.nodes[n_id] = new_node
        self.node_lookup[lookup_key] = n_id
        return new_node

    def add_edge(
        self,
        user_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Add or merge a relationship between two nodes belonging to the same user."""
        user_id_str = str(user_id)
        source_node = self.nodes.get(source_id)
        target_node = self.nodes.get(target_id)

        # Enforce user isolation: both nodes must exist and belong to user_id
        if not source_node or not target_node:
            return None
        if source_node.get("user_id") != user_id_str or target_node.get("user_id") != user_id_str:
            return None

        rel_type_clean = rel_type.upper().strip()
        lookup_key = (user_id_str, source_id, target_id, rel_type_clean)

        if lookup_key in self.edge_lookup:
            existing_id = self.edge_lookup[lookup_key]
            existing_edge = self.edges[existing_id]
            if properties:
                existing_edge["properties"].update(properties)
            existing_edge["updated_at"] = utcnow()
            return existing_edge

        e_id = edge_id or str(uuid.uuid4())
        new_edge = {
            "id": e_id,
            "user_id": user_id_str,
            "source": source_id,
            "target": target_id,
            "type": rel_type_clean,
            "properties": properties or {},
            "created_at": utcnow(),
            "updated_at": utcnow()
        }
        self.edges[e_id] = new_edge
        self.edge_lookup[lookup_key] = e_id
        return new_edge

    def get_nodes(
        self,
        user_id: str,
        label: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 300
    ) -> List[Dict[str, Any]]:
        """Retrieve user's nodes with optional label and search term filtering."""
        user_id_str = str(user_id)
        results = []
        search_lower = search.lower().strip() if search else None

        for n in self.nodes.values():
            if n["user_id"] != user_id_str:
                continue
            if label and n["label"] != label:
                continue
            if search_lower and search_lower not in n["name"].lower() and search_lower not in n["label"].lower():
                continue
            results.append(n)
            if len(results) >= limit:
                break
        return results

    def get_edges(
        self,
        user_id: str,
        rel_type: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Retrieve user's relationships."""
        user_id_str = str(user_id)
        results = []
        for e in self.edges.values():
            if e["user_id"] != user_id_str:
                continue
            if rel_type and e["type"] != rel_type.upper():
                continue
            results.append(e)
            if len(results) >= limit:
                break
        return results

    def delete_node(self, user_id: str, node_id: str) -> bool:
        """Delete a node and all incident edges belonging to user."""
        user_id_str = str(user_id)
        node = self.nodes.get(node_id)
        if not node or node["user_id"] != user_id_str:
            return False

        # Remove from lookup
        lookup_key = (user_id_str, node["label"], node["normalized_name"])
        self.node_lookup.pop(lookup_key, None)
        del self.nodes[node_id]

        # Remove incident edges
        edges_to_delete = [
            e_id for e_id, e in self.edges.items()
            if e["user_id"] == user_id_str and (e["source"] == node_id or e["target"] == node_id)
        ]
        for e_id in edges_to_delete:
            edge = self.edges.pop(e_id, None)
            if edge:
                e_lookup = (user_id_str, edge["source"], edge["target"], edge["type"])
                self.edge_lookup.pop(e_lookup, None)
        return True

    def clear_user_graph(self, user_id: str):
        """Reset all graph data for a specific user."""
        user_id_str = str(user_id)
        node_ids_to_del = [n_id for n_id, n in self.nodes.items() if n["user_id"] == user_id_str]
        for n_id in node_ids_to_del:
            node = self.nodes.pop(n_id)
            lookup_key = (user_id_str, node["label"], node["normalized_name"])
            self.node_lookup.pop(lookup_key, None)

        edge_ids_to_del = [e_id for e_id, e in self.edges.items() if e["user_id"] == user_id_str]
        for e_id in edge_ids_to_del:
            edge = self.edges.pop(e_id)
            e_lookup = (user_id_str, edge["source"], edge["target"], edge["type"])
            self.edge_lookup.pop(e_lookup, None)

    def get_neighborhood(
        self,
        user_id: str,
        node_id: Optional[str] = None,
        depth: int = 2,
        limit: int = 150
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Breadth-first search graph traversal starting from node_id up to depth hops."""
        user_id_str = str(user_id)

        if not node_id:
            # Return top connected nodes
            all_nodes = self.get_nodes(user_id_str, limit=limit)
            node_ids = {n["id"] for n in all_nodes}
            all_edges = [
                e for e in self.edges.values()
                if e["user_id"] == user_id_str and e["source"] in node_ids and e["target"] in node_ids
            ]
            return {"nodes": all_nodes, "edges": all_edges}

        root_node = self.nodes.get(node_id)
        if not root_node or root_node["user_id"] != user_id_str:
            return {"nodes": [], "edges": []}

        visited_nodes: Set[str] = {node_id}
        visited_edges: Set[str] = set()
        current_frontier = {node_id}

        for _ in range(depth):
            next_frontier = set()
            for curr in current_frontier:
                for e_id, edge in self.edges.items():
                    if edge["user_id"] != user_id_str:
                        continue
                    if edge["source"] == curr:
                        visited_edges.add(e_id)
                        target = edge["target"]
                        if target not in visited_nodes:
                            visited_nodes.add(target)
                            next_frontier.add(target)
                    elif edge["target"] == curr:
                        visited_edges.add(e_id)
                        source = edge["source"]
                        if source not in visited_nodes:
                            visited_nodes.add(source)
                            next_frontier.add(source)

                if len(visited_nodes) >= limit:
                    break
            current_frontier = next_frontier
            if not current_frontier or len(visited_nodes) >= limit:
                break

        res_nodes = [self.nodes[nid] for nid in visited_nodes if nid in self.nodes]
        res_edges = [self.edges[eid] for eid in visited_edges if eid in self.edges]
        return {"nodes": res_nodes, "edges": res_edges}

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Compute summary statistics for user's knowledge graph."""
        user_id_str = str(user_id)
        node_counts: Dict[str, int] = {}
        edge_counts: Dict[str, int] = {}

        total_nodes = 0
        for n in self.nodes.values():
            if n["user_id"] == user_id_str:
                total_nodes += 1
                lbl = n["label"]
                node_counts[lbl] = node_counts.get(lbl, 0) + 1

        total_edges = 0
        for e in self.edges.values():
            if e["user_id"] == user_id_str:
                total_edges += 1
                typ = e["type"]
                edge_counts[typ] = edge_counts.get(typ, 0) + 1

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_counts": node_counts,
            "edge_counts": edge_counts
        }

    def execute_cypher(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """In-memory Cypher pattern matching engine supporting standard read queries."""
        p = params or {}
        user_id = str(p.get("user_id", ""))
        c_lower = cypher.lower().strip()

        # 1. Project -> USES -> Technology query
        # Example: MATCH (p:Project)-[:USES]->(t:Technology) WHERE toLower(t.name) CONTAINS $tech
        if "project" in c_lower and "uses" in c_lower and "technology" in c_lower:
            tech_filter = p.get("tech_name", p.get("technology", p.get("tech", ""))).lower().strip()
            records = []
            for e in self.edges.values():
                if user_id and e["user_id"] != user_id:
                    continue
                if e["type"] == "USES":
                    src = self.nodes.get(e["source"])
                    tgt = self.nodes.get(e["target"])
                    if src and tgt and src.get("label") == "Project" and tgt.get("label") == "Technology":
                        if not tech_filter or tech_filter in tgt["name"].lower():
                            records.append({
                                "project": src["name"],
                                "technology": tgt["name"],
                                "project_id": src["id"],
                                "technology_id": tgt["id"],
                                "p": src,
                                "t": tgt,
                                "r": e
                            })
            return records

        # 2. User -> OWNS -> Project query
        if "user" in c_lower and "owns" in c_lower and "project" in c_lower:
            records = []
            for e in self.edges.values():
                if user_id and e["user_id"] != user_id:
                    continue
                if e["type"] == "OWNS":
                    src = self.nodes.get(e["source"])
                    tgt = self.nodes.get(e["target"])
                    if src and tgt and src.get("label") == "User" and tgt.get("label") == "Project":
                        records.append({
                            "user": src["name"],
                            "project": tgt["name"],
                            "project_id": tgt["id"],
                            "p": tgt,
                            "u": src
                        })
            return records

        # 3. User -> KNOWS -> Skill query
        if "user" in c_lower and "knows" in c_lower and "skill" in c_lower:
            records = []
            for e in self.edges.values():
                if user_id and e["user_id"] != user_id:
                    continue
                if e["type"] == "KNOWS":
                    src = self.nodes.get(e["source"])
                    tgt = self.nodes.get(e["target"])
                    if src and tgt and src.get("label") == "User" and tgt.get("label") == "Skill":
                        records.append({
                            "skill": tgt["name"],
                            "skill_id": tgt["id"],
                            "s": tgt,
                            "u": src
                        })
            return records

        # 4. Job -> REQUIRES -> Skill query
        if "job" in c_lower and "requires" in c_lower and "skill" in c_lower:
            skill_filter = p.get("skill_name", "").lower().strip()
            records = []
            for e in self.edges.values():
                if user_id and e["user_id"] != user_id:
                    continue
                if e["type"] == "REQUIRES":
                    src = self.nodes.get(e["source"])
                    tgt = self.nodes.get(e["target"])
                    if src and tgt and src.get("label") == "Job" and tgt.get("label") == "Skill":
                        if not skill_filter or skill_filter in tgt["name"].lower():
                            records.append({
                                "job": src["name"],
                                "skill": tgt["name"],
                                "j": src,
                                "s": tgt
                            })
            return records

        # 5. Task -> SUPPORTS -> Goal query
        if "task" in c_lower and "supports" in c_lower and "goal" in c_lower:
            records = []
            for e in self.edges.values():
                if user_id and e["user_id"] != user_id:
                    continue
                if e["type"] == "SUPPORTS":
                    src = self.nodes.get(e["source"])
                    tgt = self.nodes.get(e["target"])
                    if src and tgt and src.get("label") == "Task" and tgt.get("label") == "Goal":
                        records.append({
                            "task": src["name"],
                            "goal": tgt["name"],
                            "t": src,
                            "g": tgt
                        })
            return records

        # 6. Event -> RELATES_TO -> Project query
        if "event" in c_lower and "relates_to" in c_lower and "project" in c_lower:
            records = []
            for e in self.edges.values():
                if user_id and e["user_id"] != user_id:
                    continue
                if e["type"] == "RELATES_TO":
                    src = self.nodes.get(e["source"])
                    tgt = self.nodes.get(e["target"])
                    if src and tgt and src.get("label") == "Event" and tgt.get("label") == "Project":
                        records.append({
                            "event": src["name"],
                            "project": tgt["name"],
                            "e": src,
                            "p": tgt
                        })
            return records

        # 7. Document -> DESCRIBES -> Project query
        if "document" in c_lower and "describes" in c_lower and "project" in c_lower:
            records = []
            for e in self.edges.values():
                if user_id and e["user_id"] != user_id:
                    continue
                if e["type"] == "DESCRIBES":
                    src = self.nodes.get(e["source"])
                    tgt = self.nodes.get(e["target"])
                    if src and tgt and src.get("label") == "Document" and tgt.get("label") == "Project":
                        records.append({
                            "document": src["name"],
                            "project": tgt["name"],
                            "d": src,
                            "p": tgt
                        })
            return records

        # 8. Generic label match: MATCH (n:Label) RETURN n
        label_match = re.search(r'match\s*\(\w+:([A-Za-z]+)', c_lower)
        if label_match:
            target_label = label_match.group(1).title()
            user_nodes = [
                {"n": n, "name": n["name"], "label": n["label"], "id": n["id"]}
                for n in self.nodes.values()
                if (not user_id or n["user_id"] == user_id) and n["label"].lower() == target_label.lower()
            ]
            return user_nodes

        # Default fallback: return all user nodes
        return [
            {"n": n, "name": n["name"], "label": n["label"], "id": n["id"]}
            for n in self.nodes.values()
            if not user_id or n["user_id"] == user_id
        ]


class Neo4jClient:
    """Unified Neo4j client with native driver execution and transparent in-memory fallback."""

    def __init__(self):
        self.driver = None
        self.is_connected = False
        self.memory_store = InMemoryGraphStore()
        self._initialized = False

    async def connect(self):
        """Attempt connection to real Neo4j; fall back gracefully if unavailable."""
        if self._initialized:
            return

        try:
            import neo4j
            from neo4j import AsyncGraphDatabase

            auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=auth,
                connection_timeout=1.5
            )
            # Verify connectivity
            await self.driver.verify_connectivity()
            self.is_connected = True
            logger.info(f"Connected to Neo4j instance at {settings.NEO4J_URI}")
            await self._create_constraints()
        except Exception as e:
            self.is_connected = False
            self.driver = None
            logger.info(f"Neo4j offline or unreachable ({str(e)}). Using in-memory graph repository.")

        self._initialized = True

    async def _create_constraints(self):
        """Ensure uniqueness constraints in Neo4j."""
        if not self.is_connected or not self.driver:
            return
        labels = [
            "User", "Project", "Skill", "Technology", "Document",
            "Task", "Goal", "Event", "Company", "Job", "Topic"
        ]
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                for label in labels:
                    if label == "User":
                        await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
                    else:
                        await session.run(
                            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) "
                            f"REQUIRE (n.user_id, n.normalized_name) IS UNIQUE"
                        )
        except Exception as e:
            logger.warning(f"Could not apply Neo4j constraints: {e}")

    async def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            self.is_connected = False

    async def add_node(
        self,
        user_id: str,
        label: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store or merge node in Neo4j / memory store."""
        user_id_str = str(user_id)
        # Always update memory store for consistent fast retrieval and tests
        node = self.memory_store.add_node(
            user_id=user_id_str,
            label=label,
            name=name,
            properties=properties,
            node_id=node_id
        )

        if self.is_connected and self.driver:
            try:
                query = (
                    f"MERGE (n:{label} {{user_id: $user_id, normalized_name: $normalized_name}}) "
                    f"ON CREATE SET n.id = $id, n.name = $name, n.created_at = datetime(), n += $props "
                    f"ON MATCH SET n.name = $name, n.updated_at = datetime(), n += $props "
                    f"RETURN n"
                )
                async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                    await session.run(query, {
                        "user_id": user_id_str,
                        "normalized_name": node["normalized_name"],
                        "id": node["id"],
                        "name": node["name"],
                        "props": properties or {}
                    })
            except Exception as e:
                logger.warning(f"Neo4j add_node error: {e}")

        return node

    async def add_edge(
        self,
        user_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Store or merge relationship in Neo4j / memory store."""
        user_id_str = str(user_id)
        edge = self.memory_store.add_edge(
            user_id=user_id_str,
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            properties=properties,
            edge_id=edge_id
        )
        if not edge:
            return None

        if self.is_connected and self.driver:
            try:
                rel_clean = rel_type.upper().strip()
                query = (
                    f"MATCH (a {{id: $source_id, user_id: $user_id}}) "
                    f"MATCH (b {{id: $target_id, user_id: $user_id}}) "
                    f"MERGE (a)-[r:{rel_clean}]->(b) "
                    f"ON CREATE SET r.id = $id, r.created_at = datetime(), r += $props "
                    f"ON MATCH SET r.updated_at = datetime(), r += $props "
                    f"RETURN r"
                )
                async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                    await session.run(query, {
                        "user_id": user_id_str,
                        "source_id": source_id,
                        "target_id": target_id,
                        "id": edge["id"],
                        "props": properties or {}
                    })
            except Exception as e:
                logger.warning(f"Neo4j add_edge error: {e}")

        return edge

    async def get_nodes(
        self,
        user_id: str,
        label: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 300
    ) -> List[Dict[str, Any]]:
        return self.memory_store.get_nodes(user_id=user_id, label=label, search=search, limit=limit)

    async def get_edges(
        self,
        user_id: str,
        rel_type: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        return self.memory_store.get_edges(user_id=user_id, rel_type=rel_type, limit=limit)

    async def delete_node(self, user_id: str, node_id: str) -> bool:
        user_id_str = str(user_id)
        success = self.memory_store.delete_node(user_id=user_id_str, node_id=node_id)
        if success and self.is_connected and self.driver:
            try:
                query = "MATCH (n {id: $node_id, user_id: $user_id}) DETACH DELETE n"
                async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                    await session.run(query, {"node_id": node_id, "user_id": user_id_str})
            except Exception as e:
                logger.warning(f"Neo4j delete_node error: {e}")
        return success

    async def clear_user_graph(self, user_id: str):
        user_id_str = str(user_id)
        self.memory_store.clear_user_graph(user_id=user_id_str)
        if self.is_connected and self.driver:
            try:
                query = "MATCH (n {user_id: $user_id}) DETACH DELETE n"
                async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                    await session.run(query, {"user_id": user_id_str})
            except Exception as e:
                logger.warning(f"Neo4j clear_user_graph error: {e}")

    async def get_neighborhood(
        self,
        user_id: str,
        node_id: Optional[str] = None,
        depth: int = 2,
        limit: int = 150
    ) -> Dict[str, List[Dict[str, Any]]]:
        return self.memory_store.get_neighborhood(user_id=user_id, node_id=node_id, depth=depth, limit=limit)

    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        return self.memory_store.get_stats(user_id=user_id)

    async def execute_cypher(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute Cypher query against Neo4j if connected, else against memory store."""
        if self.is_connected and self.driver:
            try:
                async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                    result = await session.run(cypher, params or {})
                    records = await result.data()
                    return records
            except Exception as e:
                logger.warning(f"Neo4j query error: {e}. Falling back to memory store.")

        return self.memory_store.execute_cypher(cypher, params)

neo4j_client = Neo4jClient()
