import os
import requests
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# ── Configuración ──────────────────────────────────────────────────────────
load_dotenv()

MOCKAROO_API_KEY = os.getenv("MOCKAROO_API_KEY")
SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_KEY     = os.getenv("SUPABASE_KEY")
RECORD_COUNT     = 100


# ══════════════════════════════════════════════════════════════════════════
# EXTRACT — Obtener datos desde Mockaroo
# ══════════════════════════════════════════════════════════════════════════

def extract_finanzas() -> pd.DataFrame:
    """
    Extrae la tabla Finanzas desde Mockaroo.
    Campos: bank, account_number, adviser, email, status, company
    """
    print("🟦 [EXTRACT] Tabla Finanzas...")
    params = [
        ("fields[0][name]",  "bank"),
        ("fields[0][type]",  "Bank Name"),

        ("fields[1][name]",  "account_number"),
        ("fields[1][type]",  "Bank Account (IBAN)"),

        ("fields[2][name]",  "adviser"),
        ("fields[2][type]",  "Full Name"),

        ("fields[3][name]",  "email"),
        ("fields[3][type]",  "Email Address"),

        ("fields[4][name]",  "status"),
        ("fields[4][type]",  "Custom List"),
        ("fields[4][values]","Active,Inactive,Pending,Suspended"),

        ("fields[5][name]",  "company"),
        ("fields[5][type]",  "Company Name"),
    ]
    return _fetch_mockaroo(params, "Finanzas")


def extract_recursos_humanos() -> pd.DataFrame:
    """
    Extrae la tabla Recursos Humanos desde Mockaroo.
    Campos: id, first_name, last_name, email, gender, class
    """
    print("🟦 [EXTRACT] Tabla Recursos Humanos...")
    params = [
        ("fields[0][name]",  "id"),
        ("fields[0][type]",  "Row Number"),

        ("fields[1][name]",  "first_name"),
        ("fields[1][type]",  "First Name"),

        ("fields[2][name]",  "last_name"),
        ("fields[2][type]",  "Last Name"),

        ("fields[3][name]",  "email"),
        ("fields[3][type]",  "Email Address"),

        ("fields[4][name]",  "gender"),
        ("fields[4][type]",  "Gender"),

        ("fields[5][name]",  "class"),
        ("fields[5][type]",  "Custom List"),
        ("fields[5][values]","Junior,Mid,Senior,Lead,Manager"),
    ]
    return _fetch_mockaroo(params, "Recursos Humanos")


def extract_sistema_usuarios() -> pd.DataFrame:
    """
    Extrae la tabla Sistema Usuarios desde Mockaroo.
    Campos: id, first_name, last_name, email, gender, ip_address
    """
    print("🟦 [EXTRACT] Tabla Sistema Usuarios...")
    params = [
        ("fields[0][name]",  "id"),
        ("fields[0][type]",  "Row Number"),

        ("fields[1][name]",  "first_name"),
        ("fields[1][type]",  "First Name"),

        ("fields[2][name]",  "last_name"),
        ("fields[2][type]",  "Last Name"),

        ("fields[3][name]",  "email"),
        ("fields[3][type]",  "Email Address"),

        ("fields[4][name]",  "gender"),
        ("fields[4][type]",  "Gender"),

        ("fields[5][name]",  "ip_address"),
        ("fields[5][type]",  "IP Address v4"),
    ]
    return _fetch_mockaroo(params, "Sistema Usuarios")


def _fetch_mockaroo(params: list, tabla: str) -> pd.DataFrame:
    """Función interna que realiza la llamada a la API de Mockaroo."""
    url = f"https://api.mockaroo.com/api/generate.json?key={MOCKAROO_API_KEY}&count={RECORD_COUNT}"
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            raise Exception(f"Error Mockaroo [{tabla}]: {response.status_code} — {response.text}")
        df = pd.DataFrame(response.json())
        print(f"   ✅ {len(df)} registros extraídos de '{tabla}'.")
        return df
    except Exception as e:
        print(f"   ❌ Error extrayendo '{tabla}': {e}")
        raise


# ══════════════════════════════════════════════════════════════════════════
# TRANSFORM — Transformaciones por tabla
# ══════════════════════════════════════════════════════════════════════════

def transform_finanzas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transformaciones aplicadas a la tabla Finanzas:
    1. Limpieza     — eliminar nulos y emails inválidos
    2. Normalización — texto estandarizado, status en mayúsculas
    3. Enriquecimiento — columna 'risk_level' basada en status
    4. Deduplicación  — por account_number
    5. Auditoría      — timestamp de carga
    """
    print("\n🟪 [TRANSFORM] Tabla Finanzas...")
    total_orig = len(df)

    # 1. LIMPIEZA — eliminar filas con nulos
    df = df.dropna()
    print(f"   Limpieza nulos       : {total_orig - len(df)} registros eliminados.")

    # 1b. LIMPIEZA — validar formato de email
    df = df[df["email"].str.contains(r"^[^@]+@[^@]+\.[^@]+$", regex=True, na=False)]
    print(f"   Validación emails    : {len(df)} registros válidos.")

    # 2. NORMALIZACIÓN
    df["bank"]           = df["bank"].str.strip().str.title()
    df["adviser"]        = df["adviser"].str.strip().str.title()
    df["email"]          = df["email"].str.strip().str.lower()
    df["status"]         = df["status"].str.strip().str.upper()
    df["company"]        = df["company"].str.strip().str.title()
    df["account_number"] = df["account_number"].str.strip()
    print("   Normalización        : texto estandarizado.")

    # 3. ENRIQUECIMIENTO — nivel de riesgo según status
    risk_map = {
        "ACTIVE":    "Bajo",
        "PENDING":   "Medio",
        "INACTIVE":  "Alto",
        "SUSPENDED": "Crítico",
    }
    df["risk_level"] = df["status"].map(risk_map).fillna("Desconocido")
    print("   Enriquecimiento      : columna 'risk_level' calculada.")

    # 4. DEDUPLICACIÓN — por número de cuenta
    antes = len(df)
    df = df.drop_duplicates(subset=["account_number"])
    print(f"   Deduplicación        : {antes - len(df)} duplicados eliminados.")

    # 5. AUDITORÍA
    df["fecha_carga"] = datetime.utcnow().isoformat()

    print(f"   ✅ {len(df)} registros listos para cargar.")
    return df


def transform_recursos_humanos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transformaciones aplicadas a Recursos Humanos:
    1. Limpieza     — nulos y emails inválidos
    2. Normalización — nombres y género estandarizados
    3. Enriquecimiento — columna 'full_name' y 'seniority_order'
    4. Agregación   — columna 'total_por_clase' (conteo por class)
    5. Deduplicación  — por email
    """
    print("\n🟪 [TRANSFORM] Tabla Recursos Humanos...")
    total_orig = len(df)

    # 1. LIMPIEZA
    df = df.dropna()
    print(f"   Limpieza nulos       : {total_orig - len(df)} registros eliminados.")
    df = df[df["email"].str.contains(r"^[^@]+@[^@]+\.[^@]+$", regex=True, na=False)]
    print(f"   Validación emails    : {len(df)} registros válidos.")

    # 2. NORMALIZACIÓN
    df["first_name"] = df["first_name"].str.strip().str.title()
    df["last_name"]  = df["last_name"].str.strip().str.title()
    df["email"]      = df["email"].str.strip().str.lower()
    df["gender"]     = df["gender"].str.strip().str.capitalize()
    df["class"]      = df["class"].str.strip().str.title()
    print("   Normalización        : nombres y género estandarizados.")

    # 3. ENRIQUECIMIENTO — nombre completo y orden de seniority
    df["full_name"] = df["first_name"] + " " + df["last_name"]
    seniority_order = {"Junior": 1, "Mid": 2, "Senior": 3, "Lead": 4, "Manager": 5}
    df["seniority_order"] = df["class"].map(seniority_order).fillna(0).astype(int)
    print("   Enriquecimiento      : columnas 'full_name' y 'seniority_order'.")

    # 4. AGREGACIÓN — conteo de empleados por clase
    conteo = df.groupby("class")["id"].count().reset_index()
    conteo.columns = ["class", "total_por_clase"]
    df = df.merge(conteo, on="class", how="left")
    print("   Agregación           : columna 'total_por_clase' calculada.")

    # 5. DEDUPLICACIÓN
    antes = len(df)
    df = df.drop_duplicates(subset=["email"])
    print(f"   Deduplicación        : {antes - len(df)} duplicados eliminados.")

    # AUDITORÍA
    df["fecha_carga"] = datetime.utcnow().isoformat()
    df = df.drop(columns=["id"], errors="ignore")

    print(f"   ✅ {len(df)} registros listos para cargar.")
    return df


def transform_sistema_usuarios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transformaciones aplicadas a Sistema Usuarios:
    1. Limpieza     — nulos y emails inválidos
    2. Normalización — nombres en title case, email en minúsculas
    3. Enriquecimiento — columna 'ip_version' y 'full_name'
    4. Agregación   — columna 'total_por_genero'
    5. Deduplicación  — por email e ip_address
    """
    print("\n🟪 [TRANSFORM] Tabla Sistema Usuarios...")
    total_orig = len(df)

    # 1. LIMPIEZA
    df = df.dropna()
    print(f"   Limpieza nulos       : {total_orig - len(df)} registros eliminados.")
    df = df[df["email"].str.contains(r"^[^@]+@[^@]+\.[^@]+$", regex=True, na=False)]
    print(f"   Validación emails    : {len(df)} registros válidos.")

    # Validar IPs (formato básico x.x.x.x)
    df = df[df["ip_address"].str.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", na=False)]
    print(f"   Validación IPs       : {len(df)} registros con IP válida.")

    # 2. NORMALIZACIÓN
    df["first_name"] = df["first_name"].str.strip().str.title()
    df["last_name"]  = df["last_name"].str.strip().str.title()
    df["email"]      = df["email"].str.strip().str.lower()
    df["gender"]     = df["gender"].str.strip().str.capitalize()
    print("   Normalización        : texto estandarizado.")

    # 3. ENRIQUECIMIENTO
    df["full_name"]   = df["first_name"] + " " + df["last_name"]
    df["ip_version"]  = "IPv4"
    df["ip_class"]    = df["ip_address"].apply(_clasificar_ip)
    print("   Enriquecimiento      : columnas 'full_name', 'ip_version', 'ip_class'.")

    # 4. AGREGACIÓN — conteo por género
    conteo = df.groupby("gender")["id"].count().reset_index()
    conteo.columns = ["gender", "total_por_genero"]
    df = df.merge(conteo, on="gender", how="left")
    print("   Agregación           : columna 'total_por_genero' calculada.")

    # 5. DEDUPLICACIÓN
    antes = len(df)
    df = df.drop_duplicates(subset=["email"])
    df = df.drop_duplicates(subset=["ip_address"])
    print(f"   Deduplicación        : {antes - len(df)} duplicados eliminados.")

    # AUDITORÍA
    df["fecha_carga"] = datetime.utcnow().isoformat()
    df = df.drop(columns=["id"], errors="ignore")

    print(f"   ✅ {len(df)} registros listos para cargar.")
    return df


def _clasificar_ip(ip: str) -> str:
    """Clasifica una IP según su primer octeto (clases A, B, C)."""
    try:
        primer_octeto = int(ip.split(".")[0])
        if primer_octeto <= 126:
            return "Clase A"
        elif primer_octeto <= 191:
            return "Clase B"
        elif primer_octeto <= 223:
            return "Clase C"
        else:
            return "Especial"
    except Exception:
        return "Desconocida"


# ══════════════════════════════════════════════════════════════════════════
# LOAD — Cargar datos en Supabase
# ══════════════════════════════════════════════════════════════════════════

def load(df: pd.DataFrame, client: Client, tabla: str) -> int:
    """
    Carga los datos transformados en Supabase por lotes de 50 registros.
    Retorna el total de registros cargados.
    """
    print(f"\n🟩 [LOAD] Cargando tabla '{tabla}' en Supabase...")
    registros      = df.to_dict(orient="records")
    batch_size     = 50
    total_cargados = 0

    for i in range(0, len(registros), batch_size):
        lote = registros[i:i + batch_size]
        try:
            response = client.table(tabla).insert(lote).execute()
            if hasattr(response, "data") and response.data:
                total_cargados += len(response.data)
                print(f"   Lote {i // batch_size + 1}: {len(response.data)} registros insertados.")
            else:
                print(f"   ⚠️  Lote {i // batch_size + 1}: posible problema — {response}")
        except Exception as e:
            print(f"   ❌ Error en lote {i // batch_size + 1}: {e}")

    print(f"   ✅ Total cargado en '{tabla}': {total_cargados} registros.")
    return total_cargados


# ══════════════════════════════════════════════════════════════════════════
# MONITOREO — Resumen del pipeline
# ══════════════════════════════════════════════════════════════════════════

def log_resumen(resultados: list) -> None:
    print("\n" + "=" * 58)
    print("📊 RESUMEN DEL PIPELINE ETL")
    print("=" * 58)
    total_extraidos = 0
    total_cargados  = 0
    for nombre, extraidos, cargados in resultados:
        descartados  = extraidos - cargados
        tasa         = cargados / extraidos * 100 if extraidos > 0 else 0
        total_extraidos += extraidos
        total_cargados  += cargados
        print(f"\n  Tabla            : {nombre}")
        print(f"  Extraídos        : {extraidos}")
        print(f"  Cargados         : {cargados}")
        print(f"  Descartados      : {descartados}")
        print(f"  Tasa de éxito    : {tasa:.1f}%")
    print("\n" + "-" * 58)
    tasa_global = total_cargados / total_extraidos * 100 if total_extraidos > 0 else 0
    print(f"  TOTAL EXTRAÍDOS  : {total_extraidos}")
    print(f"  TOTAL CARGADOS   : {total_cargados}")
    print(f"  TASA GLOBAL      : {tasa_global:.1f}%")
    print(f"  FECHA EJECUCIÓN  : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 58)


# ══════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def run_pipeline():
    print("=" * 58)
    print("   PIPELINE ETL — Mockaroo → Supabase")
    print("   Tablas: Finanzas | Recursos Humanos | Sistema Usuarios")
    print("=" * 58 + "\n")

    inicio = datetime.utcnow()

    # Validar credenciales
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ERROR: Faltan las credenciales de Supabase en el archivo .env")
        print("   Asegúrate de tener SUPABASE_URL y SUPABASE_KEY correctos.")
        return

    # Conexión a Supabase
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("🔗 Conexión a Supabase establecida.\n")
    except Exception as e:
        print(f"❌ ERROR conectando a Supabase: {e}")
        return

    resultados = []

    # ── FINANZAS ──────────────────────────────────────────────────────────
    try:
        df_fin_raw   = extract_finanzas()
        df_fin_clean = transform_finanzas(df_fin_raw)
        cargados_fin = load(df_fin_clean, supabase, "finanzas")
        resultados.append(("Finanzas", len(df_fin_raw), cargados_fin))
    except Exception as e:
        print(f"❌ Pipeline Finanzas falló: {e}")
        resultados.append(("Finanzas", 0, 0))

    # ── RECURSOS HUMANOS ──────────────────────────────────────────────────
    try:
        df_rh_raw   = extract_recursos_humanos()
        df_rh_clean = transform_recursos_humanos(df_rh_raw)
        cargados_rh = load(df_rh_clean, supabase, "recursos_humanos")
        resultados.append(("Recursos Humanos", len(df_rh_raw), cargados_rh))
    except Exception as e:
        print(f"❌ Pipeline Recursos Humanos falló: {e}")
        resultados.append(("Recursos Humanos", 0, 0))

    # ── SISTEMA USUARIOS ──────────────────────────────────────────────────
    try:
        df_us_raw   = extract_sistema_usuarios()
        df_us_clean = transform_sistema_usuarios(df_us_raw)
        cargados_us = load(df_us_clean, supabase, "sistema_usuarios")
        resultados.append(("Sistema Usuarios", len(df_us_raw), cargados_us))
    except Exception as e:
        print(f"❌ Pipeline Sistema Usuarios falló: {e}")
        resultados.append(("Sistema Usuarios", 0, 0))

    # ── RESUMEN ───────────────────────────────────────────────────────────
    log_resumen(resultados)
    duracion = (datetime.utcnow() - inicio).seconds
    print(f"\n✅ Pipeline finalizado en {duracion} segundos.")


if __name__ == "__main__":
    run_pipeline()