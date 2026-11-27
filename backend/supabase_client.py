
import httpx
from supabase import Client, create_client as _create_client
from supabase.lib.client_options import SyncClientOptions


def create_client(supabase_url: str, supabase_key: str) -> Client:
    """
    Create a Supabase client using a shared HTTP/1.1 transport.

    HTTP/2 is disabled to avoid the HTTP/2 connection-state errors
    observed in concurrent Supabase requests.
    """
    http_client = httpx.Client(
        http2=False,
        timeout=httpx.Timeout(120.0, connect=10.0),
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
        ),
    )

    options = SyncClientOptions(
        httpx_client=http_client,
        postgrest_client_timeout=120,
    )

    return _create_client(
        supabase_url,
        supabase_key,
        options=options,
    )
