from firebase_admin import messaging


class FCMManager:
    def send_fcm_message(title, body, device_tokens):
        messages = []
        for token in device_tokens:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                token=token,
            )
            messages.append(message)

        try:
            response = messaging.send_each(messages)
            for i, resp in enumerate(response.responses):
                if not resp.success:
                    pass

            return response
        except Exception:  # noqa
            return None
