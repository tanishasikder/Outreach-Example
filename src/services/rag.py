import json
from qdrant_client import QdrantClient
from qdrant_client.models import Document
from src.models.vector import COLLECTION, EMBED_MODEL

# Gets sales tips from PDF files that fit the predicted company
def get_info(client: QdrantClient, report: dict, limit: int = 5) -> list[str]:
    inputs = report['inputs']
    query_text = (
        f"Sales outreach pipeline tips for a {inputs['industry']} company "
        f"at the {inputs['funding_stage']} stage (lead source: {inputs['lead_source']}), "
        f"where the deal is likely to be {report['predicted_label']}"
    )
    results = client.query_points(
        collection_name=COLLECTION,
        query=Document(text=query_text, model=EMBED_MODEL), # Same model as the stored chunks
        with_payload=True,
        limit=limit
    )
    return [point.payload['text'] for point in results.points]

def make_output(report: dict, llm, client: QdrantClient) -> str:
    '''Writes the sales report from the prediction and the retrieved tips'''
    tips = '\n\n---\n\n'.join(get_info(client, report))
    query_text = f"""
        You are a helpful sales associate. The information below
        shows the predictions of a company. Is the company interested in the
        product? How confident is it? Using the tips and the data,
        generate a report describing tips and details to a sales team.
        Only use tips from the context below.

        prediction: {json.dumps(report)}

        tips from the sales handbooks:
        {tips}
    """
    response = llm.invoke(query_text)
    return str(response.text) # Plain str so Celery can store it as JSON
