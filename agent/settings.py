from agents import ModelSettings


def get_settings() -> ModelSettings:
    return ModelSettings(
        store=False,  # از ذخیره‌شدن Response برای بازیابی بعدی جلوگیری می‌کند
        # temperature=0.2,  # کنترل تصادفی‌بودن؛ عدد کمتر یعنی پاسخ قابل‌پیش‌بینی‌تر
        # top_p=0.9,  # جایگزین temperature برای nucleus sampling؛ معمولاً فقط یکی از این دو تنظیم می‌شود
        # frequency_penalty=0.4,  # کاهش تکرار مکرر کلمات و عبارت‌ها
        # presence_penalty=0.3,  # تشویق مدل به مطرح‌کردن موضوع‌ها و واژه‌های جدید
        # tool_choice="auto",  # انتخاب ابزار: auto، required، none یا نام یک ابزار مشخص
        # parallel_tool_calls=True,  # اجازهٔ فراخوانی هم‌زمان چند ابزار در یک نوبت
        # truncation="auto",  # کوتاه‌کردن خودکار ورودی هنگام عبور از ظرفیت Context
        # max_tokens=1500,  # حداکثر تعداد توکن خروجی
        # reasoning={"effort": "medium"},  # میزان تلاش استدلالی؛ فقط برای مدل‌های پشتیبانی‌شده
        # verbosity="low",  # میزان جزئیات پاسخ: low، medium یا high
        # metadata={"project": "ai-agent"},  # برچسب‌هایی که همراه درخواست به Provider ارسال می‌شوند
        # prompt_cache_retention="24h",  # نگهداری Prompt Cache؛ در API جدید deprecated شده است
        # include_usage=True,  # افزودن Usage به جریان خروجی؛ مخصوص Chat Completions streaming
        # response_include=["file_search_call.results"],  # درخواست فیلدهای اضافی از Response
        # top_logprobs=5,  # برگرداندن احتمال توکن انتخاب‌شده و توکن‌های جایگزین
        # extra_query={"version": "1"},  # پارامترهای اضافی URL؛ فقط برای Providerهایی که آن را می‌شناسند
        # extra_body={"custom_option": True},  # فیلدهای اضافی JSON؛ این مقدار صرفاً نمونه است
        # extra_headers={"X-App": "agent"},  # Headerهای اضافی HTTP
        # extra_args={"provider_option": "value"},  # آرگومان اختصاصی Provider؛ این مقدار صرفاً نمونه است
        # retry={"max_retries": 2, "backoff": {"initial_delay": 0.5, "max_delay": 5, "multiplier": 2, "jitter": True}},  # تکرار درخواست در خطاهای موقت شبکه یا Provider
        # context_management=[{"type": "compaction", "compact_threshold": 200_000}],  # فشرده‌سازی Context مکالمات بسیار طولانی در Providerهای پشتیبانی‌شده
        # prompt_cache_options={"mode": "implicit", "ttl": "30m", "prewarm": False},  # تنظیم Prompt Cache برای مدل‌های پشتیبانی‌شده
        # preserve_raw_usage=True,  # نگهداری Usage خام Provider در ModelResponse.raw_usage
        # timeout=60,  # حداکثر زمان هر تلاش برای فراخوانی مدل، برحسب ثانیه
    )
