from app.infrastructure.db.document import DocumentDBManager


class DBManager:
    def __init__(self, document_db: DocumentDBManager) -> None:
        self.document_db = document_db
    