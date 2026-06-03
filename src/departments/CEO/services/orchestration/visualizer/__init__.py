"""
Workflow execution visualization.
P2-C implementation.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from departments.CIO.services.workflow_runs import WorkflowRunService


@dataclass
class DAGNode:
    """Node in workflow DAG."""
    id: str
    label: str
    status: str  # pending | running | completed | failed | skipped
    duration_ms: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'label': self.label,
            'status': self.status,
            'duration_ms': self.duration_ms,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'metadata': self.metadata or {}
        }


@dataclass
class DAGEdge:
    """Edge in workflow DAG."""
    from_node: str
    to_node: str
    label: Optional[str] = None
    style: str = "solid"  # solid | dashed | dotted
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'from': self.from_node,
            'to': self.to_node,
            'label': self.label,
            'style': self.style
        }


class WorkflowVisualizer:
    """
    Generates workflow execution DAG for visualization.
    
    Supports multiple output formats:
    - Mermaid (for Markdown/rendering)
    - Graphviz DOT (for PDF/SVG export)
    - Cytoscape JSON (for interactive web UI)
    """
    
    STAGES = [
        ('CFO', 'Budget Check'),
        ('Research', 'Hotspot Discovery'),
        ('Analysis', 'Content Analysis'),
        ('Planning', 'R&D Planning'),
        ('Production', 'Content Production'),
        ('QA', 'Quality Assurance'),
        ('Publish', 'Content Publishing')
    ]
    
    def __init__(self, run_service, artifact_service=None):
        self.run_service = run_service
        self.artifact_service = artifact_service
        
    async def generate_trace_dag(self, run_id: str) -> Dict[str, Any]:
        """
        Generate DAG for a workflow run.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            DAG with nodes and edges
        """
        run = await self._get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
            
        nodes = []
        edges = []
        
        # Create nodes for each stage
        for stage_id, stage_label in self.STAGES:
            node = await self._create_stage_node(run, stage_id, stage_label)
            nodes.append(node)
            
        # Create sequential edges
        for i in range(len(nodes) - 1):
            edges.append(DAGEdge(
                from_node=nodes[i].id,
                to_node=nodes[i + 1].id
            ))
            
        # Add QA rework loop if present
        if await self._has_qa_rework(run):
            edges.append(DAGEdge(
                from_node='QA',
                to_node='Planning',
                label='rework',
                style='dashed'
            ))
            
        # Add conditional edges based on execution path
        if run.result_payload:
            edges = self._add_conditional_edges(run.result_payload, edges)
            
        return {
            'run_id': run_id,
            'status': run.status,
            'nodes': [n.to_dict() for n in nodes],
            'edges': [e.to_dict() for e in edges],
            'created_at': run.created_at.isoformat() if run.created_at else None,
            'completed_at': run.updated_at.isoformat() if run.updated_at else None
        }

    async def _get_run(self, run_id: str):
        """Resolve workflow runs by UUID first, then numeric ID."""
        run = None
        if hasattr(self.run_service, "get_by_uuid"):
            run = await self.run_service.get_by_uuid(run_id)
        if run is None and str(run_id).isdigit():
            run = await self.run_service.get_run_by_id(int(run_id))
        return run
        
    async def _create_stage_node(self, run, stage_id: str, stage_label: str) -> DAGNode:
        """Create a DAG node for a stage."""
        stage_artifact = await self._get_stage_artifact(run, stage_id)
        
        if stage_artifact:
            status = 'completed'
            metadata = stage_artifact.get('data', {})
        else:
            # Determine status based on run status and stage order
            status = self._infer_stage_status(run, stage_id)
            metadata = {}
            
        return DAGNode(
            id=stage_id,
            label=stage_label,
            status=status,
            metadata=metadata
        )
        
    def _infer_stage_status(self, run, stage_id: str) -> str:
        """Infer stage status from run status."""
        if run.status == 'pending':
            return 'pending'
        elif run.status == 'failed':
            # Failed at some stage, determine which
            return 'failed' if self._is_failed_stage(run, stage_id) else 'skipped'
        elif run.status == 'running':
            return 'running' if self._is_current_stage(run, stage_id) else 'pending'
        return 'completed'
        
    async def _has_qa_rework(self, run) -> bool:
        """Check if QA rework occurred."""
        if self.artifact_service and hasattr(self.artifact_service, "get_artifacts"):
            artifacts = await self.artifact_service.get_artifacts(run.id)
            return any("rework" in a.get("stage", "") for a in artifacts)
        return False

    async def _get_stage_artifact(self, run, stage_id: str) -> Optional[Dict[str, Any]]:
        """Get a stage artifact from the configured service or persisted run payload."""
        if self.artifact_service and hasattr(self.artifact_service, "get_artifacts"):
            artifacts = await self.artifact_service.get_artifacts(run.id)
            return next((a for a in artifacts if a["stage"] == stage_id.lower()), None)

        result_payload = run.result_payload or {}
        payload_key_by_stage = {
            "CFO": "finance_bundle",
            "Research": "research_bundle",
            "Analysis": "analysis_bundle",
            "Planning": "prompt_bundle",
            "Production": "production_bundle",
            "QA": "qa_bundle",
            "Publish": "publish_bundle",
        }
        payload_key = payload_key_by_stage.get(stage_id)
        payload = result_payload.get(payload_key) if payload_key else None
        if not isinstance(payload, dict) or not payload:
            return None
        return {
            "stage": stage_id.lower(),
            "data": payload,
        }
        
    def _add_conditional_edges(self, result_payload: Dict, edges: List[DAGEdge]) -> List[DAGEdge]:
        """Add conditional edges based on execution path."""
        # Add publish approval edge if manual approval was needed
        if result_payload.get('publish_status') == 'pending_approval':
            edges.append(DAGEdge(
                from_node='Publish',
                to_node='Approval',
                label='manual',
                style='dotted'
            ))
            
        return edges
        
    def to_mermaid(self, dag: Dict[str, Any]) -> str:
        """
        Convert DAG to Mermaid flowchart syntax.
        
        Example output:
        ```mermaid
        flowchart TD
            CFO[CFO: Budget Check] --> Research[Research: Hotspot Discovery]
            Research --> Analysis[Analysis: Content Analysis]
            Analysis --> Planning[Planning: R&D Planning]
            Planning --> Production[Production: Content Production]
            Production --> QA[QA: Quality Assurance]
            QA --> Publish[Publish: Content Publishing]
            QA -.->|rework| Planning
        ```
        """
        lines = ["flowchart TD"]
        
        # Add nodes with status styling
        for node in dag['nodes']:
            style = self._get_mermaid_style(node['status'])
            lines.append(f"    {node['id']}[{node['label']}]:::${style}")
            
        # Add edges
        for edge in dag['edges']:
            if edge['style'] == 'dashed':
                lines.append(f"    {edge['from']} -.->|{edge.get('label', '')}| {edge['to']}")
            else:
                lines.append(f"    {edge['from']} --> {edge['to']}")
                
        # Add class definitions for styling
        lines.extend([
            "    classDef completed fill:#90EE90",
            "    classDef failed fill:#FFB6C1",
            "    classDef running fill:#87CEEB",
            "    classDef pending fill:#D3D3D3"
        ])
        
        return "\n".join(lines)
        
    def to_graphviz(self, dag: Dict[str, Any]) -> str:
        """Convert DAG to Graphviz DOT format."""
        lines = [
            'digraph Workflow {',
            '    rankdir=LR;',
            '    node [shape=box, style="rounded,filled"];'
        ]
        
        # Add nodes
        for node in dag['nodes']:
            color = self._get_graphviz_color(node['status'])
            lines.append(f'    {node["id"]} [label="{node["label"]}", fillcolor="{color}"];')
            
        # Add edges
        for edge in dag['edges']:
            if edge['style'] == 'dashed':
                lines.append(f'    {edge["from"]} -> {edge["to"]} [style=dashed, label="{edge.get("label", "")}"];')
            else:
                lines.append(f'    {edge["from"]} -> {edge["to"]};')
                
        lines.append('}')
        
        return "\n".join(lines)
        
    def to_cytoscape(self, dag: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DAG to Cytoscape.js elements format."""
        elements = []
        
        # Add nodes
        for node in dag['nodes']:
            elements.append({
                'data': {
                    'id': node['id'],
                    'label': node['label'],
                    'status': node['status']
                },
                'classes': node['status']
            })
            
        # Add edges
        for edge in dag['edges']:
            elements.append({
                'data': {
                    'id': f"{edge['from']}_{edge['to']}",
                    'source': edge['from'],
                    'target': edge['to'],
                    'label': edge.get('label', '')
                }
            })
            
        return {'elements': elements}
        
    def _get_mermaid_style(self, status: str) -> str:
        """Get Mermaid class name for status."""
        return status
        
    def _get_graphviz_color(self, status: str) -> str:
        """Get Graphviz color for status."""
        colors = {
            'completed': '#90EE90',
            'failed': '#FFB6C1',
            'running': '#87CEEB',
            'pending': '#D3D3D3',
            'skipped': '#F0F0F0'
        }
        return colors.get(status, '#FFFFFF')


# FastAPI endpoint for visualization
from fastapi import APIRouter, HTTPException

viz_router = APIRouter(prefix="/visualization", tags=["visualization"])

@viz_router.get("/runs/{run_id}/dag")
async def get_run_dag(run_id: str, format: str = "json"):
    """
    Get workflow DAG in various formats.
    
    Args:
        run_id: Workflow run ID
        format: Output format (json, mermaid, graphviz, cytoscape)
    """
    visualizer = WorkflowVisualizer(
        run_service=WorkflowRunService(),
    )
    
    try:
        dag = await visualizer.generate_trace_dag(run_id)
        
        if format == "json":
            return dag
        elif format == "mermaid":
            return {"mermaid": visualizer.to_mermaid(dag)}
        elif format == "graphviz":
            return {"dot": visualizer.to_graphviz(dag)}
        elif format == "cytoscape":
            return visualizer.to_cytoscape(dag)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown format: {format}")
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
