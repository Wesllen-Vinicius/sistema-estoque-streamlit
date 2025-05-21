# src/database.py
import os
from supabase import create_client, Client

_supabase_client = None

def get_supabase_client() -> Client:
    """
    Retorna uma instância singleton do cliente Supabase.
    Carrega as variáveis de ambiente (URL e KEY) de forma centralizada.
    """
    global _supabase_client
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Variáveis de ambiente SUPABASE_URL e SUPABASE_KEY não configuradas.")
        _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client
