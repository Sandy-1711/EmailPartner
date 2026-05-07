class EmailWatchService:
    @classmethod
    async def watch_email(cls, email_id: str) -> None:
        # TODO: enqueue pipeline processing for the email_id.
        print(f"Watching email with ID: {email_id}")
