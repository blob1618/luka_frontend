from app.models.database import SessionLocal, Usuario
db = SessionLocal()
try:
    user = db.query(Usuario).first()
    print("User query successful!")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
