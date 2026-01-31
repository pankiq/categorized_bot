from aiogram import BaseMiddleware, types

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self):
        self.flood_cache = {}

    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            text = event.text or event.caption
            
            if text: 
                if user_id in self.flood_cache:
                    last_msg = self.flood_cache[user_id]
                    if last_msg['text'] == text:
                        try:
                            await event.bot.delete_message(chat_id=event.chat.id, message_id=last_msg['msg_id'])
                        except Exception:
                            pass
                self.flood_cache[user_id] = {'text': text, 'msg_id': event.message_id}
        return await handler(event, data)
