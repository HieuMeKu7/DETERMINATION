# DETERMINATION.py
#
# A completely remade Discord bot using the Gemini API to provide spontaneous,
# engaging content with a distinct Vietnamese personality.
#
# --- SETUP ---
# 1. Install necessary libraries:
#    pip install -U py-cord google-generativeai python-dotenv
#
# 2. Create a file named DETERMINATION.env in the same directory as this script.
#
# 3. Inside the DETERMINATION.env file, add your secret keys:
#    DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
#    GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
#
# 4. Get your credentials from the Discord Developer Portal and Google AI Studio.
#
# 5. Run the bot from your terminal:
#    python DETERMINATION.py

import os
import random
import re
import time
from collections import deque
import discord
from discord.ui import InputText, Modal
import google.generativeai as genai
from dotenv import load_dotenv

# --- CORE CONFIGURATION ---
load_dotenv(dotenv_path='DETERMINATION.env')
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Discord token or Gemini API key not found in .env file.")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite')


# --- RATE LIMITING ---
class RateLimiter:

    def __init__(self, rpm_limit: int, daily_limit: int):
        self.rpm_limit = rpm_limit
        self.daily_limit = daily_limit
        self.requests_minute = deque()
        self.requests_day = deque()

    def check(self) -> tuple[bool, str]:
        """Checks if a request is allowed. Returns (is_limited, message)."""
        current_time = time.time()

        # Clean old timestamps
        while self.requests_minute and current_time - self.requests_minute[
                0] > 60:
            self.requests_minute.popleft()
        while self.requests_day and current_time - self.requests_day[0] > 86400:
            self.requests_day.popleft()

        # Check limits
        if len(self.requests_minute) >= self.rpm_limit:
            return True, "Bot đang bận suy nghĩ! Vui lòng thử lại sau một phút."
        if len(self.requests_day) >= self.daily_limit:
            return True, "Hôm nay bot đã dùng hết năng lượng rồi. Hẹn gặp lại bạn vào ngày mai nhé!"

        return False, ""

    def record_request(self):
        """Records a new request timestamp."""
        current_time = time.time()
        self.requests_minute.append(current_time)
        self.requests_day.append(current_time)


limiter = RateLimiter(rpm_limit=10, daily_limit=499)

# --- BOT INITIALIZATION ---
intents = discord.Intents.default()
bot = discord.Bot(intents=intents)


# --- GEMINI HELPER ---
async def ask_gemini(prompt: str) -> str:
    """A robust helper to query the Gemini API with error handling."""
    print(f"Querying Gemini: '{prompt[:60]}...'")
    try:
        response = gemini_model.generate_content(prompt)
        if not response.candidates:
            return "Rất tiếc, tôi không thể tạo phản hồi. Có thể nội dung đã bị chặn vì lý do an toàn."
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"Xin lỗi, có một lỗi nhỏ đã xảy ra khi tôi đang kết nối với vũ trụ: {e}"


# --- UI MODAL FOR TAROT ---
class TarotInquiryModal(Modal):

    def __init__(self, card_info: str):
        super().__init__(title="Hỏi Tarot Về Vận Mệnh")
        self.card_info = card_info
        self.add_item(
            InputText(label="Câu hỏi của bạn là gì?",
                      placeholder=
                      "Ví dụ: Sự nghiệp của tôi sắp tới sẽ có khởi sắc không?",
                      style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        question = self.children[0].value
        await interaction.response.defer(ephemeral=False)

        is_limited, msg = limiter.check()
        if is_limited:
            await interaction.followup.send(msg, ephemeral=True)
            return
        limiter.record_request()

        prompt = (
            f"Bạn là một chuyên gia Tarot sâu sắc và thấu cảm. "
            f"Lá bài đã được rút là '{self.card_info}'. Người dùng có câu hỏi: '{question}'. "
            "Hãy phân tích, kết nối ý nghĩa của lá bài với câu hỏi để đưa ra một lời khuyên chân thành, "
            "chi tiết và sâu sắc. Sử dụng ngôn ngữ tiếng Việt tự nhiên, gần gũi."
        )
        interpretation = await ask_gemini(prompt)

        embed = discord.Embed(title=f"Lời Giải Đáp Cho Lá {self.card_info}",
                              description=interpretation,
                              color=discord.Color.purple())
        embed.set_footer(
            text=f"Dành cho câu hỏi của {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)


# --- BOT EVENTS ---
@bot.event
async def on_ready():
    print(f"Bot '{bot.user.name}' đã thức giấc và sẵn sàng gieo quẻ!")
    print(f"ID: {bot.user.id}")
    print("-" * 20)


# --- BOT COMMANDS ---
@bot.slash_command(name="ping",
                   description="Kiểm tra xem bot có đang hoạt động không.")
async def ping(ctx: discord.ApplicationContext):
    await ctx.respond(
        f"Pong! Bot vẫn ở đây, với độ trễ {bot.latency*1000:.2f}ms. Sẵn sàng cho mọi cuộc vui!",
        ephemeral=True)


@bot.slash_command(name="tarot",
                   description="Rút một lá bài Tarot để xem vận mệnh hôm nay.")
async def tarot(ctx: discord.ApplicationContext):
    is_limited, msg = limiter.check()
    if is_limited:
        await ctx.respond(msg, ephemeral=True)
        return
    limiter.record_request()

    await ctx.defer()

    prompt = (
        "Bạn là một người gieo bài Tarot. Hãy rút một lá bài ngẫu nhiên từ bộ bài Tarot (Major hoặc Minor Arcana). "
        "Sau đó, chọn ngẫu nhiên trạng thái của nó (xuôi hoặc ngược). "
        "Chỉ trả về tên lá bài và trạng thái theo định dạng: 'Tên Lá Bài (Xuôi/Ngược)'. "
        "Ví dụ: 'The Magician (Upright)'. Trả lời bằng tiếng Việt.")
    card_info = await ask_gemini(prompt)

    await ctx.followup.send(
        f"Vũ trụ đã gửi một thông điệp cho {ctx.author.mention} qua lá bài **{card_info.strip()}**.\n"
        "Bạn có muốn hỏi gì thêm về lá bài này không?",
        view=TarotInquiryView(card_info.strip()))


class TarotInquiryView(discord.ui.View):

    def __init__(self, card_info: str):
        super().__init__(timeout=300)  # View times out after 5 minutes
        self.card_info = card_info

    @discord.ui.button(label="Đặt Câu Hỏi Chi Tiết",
                       style=discord.ButtonStyle.primary,
                       emoji="❓")
    async def ask_question(self, button: discord.ui.Button,
                           interaction: discord.Interaction):
        modal = TarotInquiryModal(self.card_info)
        await interaction.response.send_modal(modal)
        # Disable the button after it's clicked
        self.stop()
        button.disabled = True
        await interaction.message.edit(view=self)


@bot.slash_command(name="yesno",
                   description="Hỏi một câu hỏi Có/Không, để vũ trụ trả lời.")
async def yesno(ctx: discord.ApplicationContext, question: discord.Option(
    str, "Câu hỏi bạn muốn biết câu trả lời.")):
    is_limited, msg = limiter.check()
    if is_limited:
        await ctx.respond(msg, ephemeral=True)
        return
    limiter.record_request()

    await ctx.defer()

    answer = random.choice(["Có", "Không"])
    prompt = (
        f"Bạn là một nhà tiên tri hóm hỉnh. Với câu hỏi '{question}', "
        f"số phận đã thì thầm câu trả lời là '{answer}'. "
        "Hãy diễn giải câu trả lời này một cách đầy ẩn ý, thú vị, và đừng tiết lộ trực tiếp 'Có' hay 'Không'. "
        "Hãy trả lời bằng tiếng Việt.")

    presentation = await ask_gemini(prompt)

    embed = discord.Embed(
        title=f"Dành cho câu hỏi của {ctx.author.display_name}",
        description=f"> {question}",
        color=discord.Color.green() if answer == "Có" else discord.Color.red())
    embed.add_field(name="Vũ trụ thì thầm...", value=presentation)

    response_message = await ctx.followup.send(embed=embed)
    await response_message.add_reaction('👍' if answer == "Có" else '👎')


@bot.slash_command(name="diceroll",
                   description="Tung xúc xắc may mắn (ví dụ: 2d6, 1d20).")
async def diceroll(ctx: discord.ApplicationContext,
                   dice: discord.Option(str,
                                        "Xúc xắc cần tung (định dạng NdN).")):
    match = re.fullmatch(r'(\d+)d(\d+)', dice.lower())
    if not match:
        await ctx.respond(
            "Định dạng không đúng! Hãy dùng `NdN` (ví dụ: `2d6`, `1d20`).",
            ephemeral=True)
        return

    num_dice, num_sides = int(match.group(1)), int(match.group(2))
    if not (1 <= num_dice <= 100 and 2 <= num_sides <= 1000):
        await ctx.respond(
            "Số lượng xúc xắc (1-100) hoặc số mặt (2-1000) không hợp lệ.",
            ephemeral=True)
        return

    is_limited, msg = limiter.check()
    if is_limited:
        await ctx.respond(msg, ephemeral=True)
        return
    limiter.record_request()

    await ctx.defer()

    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    total = sum(rolls)

    prompt = (
        f"Bạn là một người dẫn truyện game đầy kịch tính. Người chơi vừa tung {dice}. "
        f"Kết quả từng viên là: {', '.join(map(str, rolls))}. Tổng điểm là {total}. "
        "Hãy tường thuật lại cảnh tung xúc xắc này một cách hào hùng và sống động. "
        "Nhấn mạnh vào kết quả cuối cùng. Hãy trả lời bằng tiếng Việt.")

    presentation = await ask_gemini(prompt)
    await ctx.followup.send(
        f"**{ctx.author.mention}** tung xúc xắc...\n\n{presentation}")


# --- RUN BOT ---
if __name__ == "__main__":
    try:
        print("Starting Discord bot...")
        bot.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print(
            "ERROR: Invalid Discord bot token. Please check your DETERMINATION.ENV file."
        )
    except Exception as e:
        print(f"ERROR: Failed to start bot: {e}")
