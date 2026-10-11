from agents import ModelSettings
from openai.types import Reasoning
from openai.types.responses.response_create_params import ContextManagement

from config import settings


def get_settings() -> ModelSettings:

    return ModelSettings(
        store=False,
        tool_choice="auto",
        parallel_tool_calls=False,
        max_tokens=settings.model_max_tokens,
        reasoning=Reasoning(effort=settings.model_reasoning, summary="auto", context="auto"),
        verbosity=settings.model_verbosity,
        context_management=[
            ContextManagement(type="compaction", compact_threshold=settings.model_context_compact)
        ],
        timeout=60,
    )


# def get_settings() -> ModelSettings:
#     return ModelSettings(
#         store=False,   از ذخیره‌شدن Response برای بازیابی بعدی جلوگیری می‌کند
#         0.0 تا 0.2: کدنویسی، ابزارها، پاسخ دقیق و باثبات
#         0.3 تا 0.5: دستیار عمومی
#         0.7 تا 1.0: ایده‌پردازی و متن خلاق
#         temperature=0,   کنترل تصادفی‌بودن؛ عدد کمتر یعنی پاسخ قابل‌پیش‌بینی‌تر
#         0  →  0.2  →  0.4
#         عدد بزگتر از تکرار جلوگیری میکند
#         frequency_penalty=0,   کاهش تکرار مکرر کلمات و عبارت‌ها
#         کدنویسی و اجرای ابزار	0
#         دستیار عمومی	0 تا 0.2
#         ایده‌پردازی	0.3 تا 0.6
#         presence_penalty=0,   تشویق مدل به مطرح‌کردن موضوع‌ها و واژه‌های جدید
#         "required" "none"
#         tool_choice="auto",   "required" "none"   انتخاب ابزار: auto، required، none یا نام یک ابزار مشخص
#         parallel_tool_calls=False,   اجازهٔ فراخوانی هم‌زمان چند ابزار در یک نوبت
#         auto قدیمی‌ترین پیام‌ها حذف می‌شوند و اجرا ادامه پیدا می‌کند
#         "disabled"	چیزی حذف نمی‌شود؛ در Context پر خطای 400 می‌گیرید
#         None	رفتار به Provider واگذار می‌شود
#         truncation="disabled",  کوتاه‌کردن خودکار ورودی هنگام عبور از ظرفیت Context
#         پاسخ خیلی کوتاه	300 تا 500
#         دستیار عمومی	1000 تا 2000
#         توضیح و تحلیل کد	2000 تا 4000
#         تولید فایل یا کد طولانی	4000 تا 8000
#         مدل reasoning با مسئلهٔ پیچیده	مقدار بالاتر یا None
#         max_tokens=None,   حداکثر تعداد توکن خروجی
#         "none"        بدون استدلال اضافه
#         "minimal"     حداقل استدلال
#         "low"      سریع و کم‌هزینه
#         "medium"   متعادل؛ پیشنهاد عمومی
#         "high"     تحلیل عمیق
#         "xhigh"    مسائل بسیار پیچیده
#         "max"      حداکثر استدلال
#         "auto"     بهترین حالت قابل پشتیبانی مدل
#         "concise"  خلاصه کوتاه
#         "detailed" خلاصه مفصل
#         "auto"           مدل تصمیم می‌گیرد
#         "current_turn"   فقط reasoning مرحله فعلی
#         "all_turns"      reasoning مراحل قبلی هم استفاده شود
#         reasoning={"effort": "medium", "summary": "concise", "context": "all_turns"},  میزان تلاش استدلالی؛ فقط برای مدل‌های پشتیبانی‌شده
#         verbosity="medium",  میزان جزئیات پاسخ: low، medium یا high
#         include_usage=True,  افزودن Usage به جریان خروجی؛ مخصوص Chat Completions streaming
#         web_search_call.results: نتیجه‌های کامل جست‌وجوی وب
#         web_search_call.action.sources: منابع و لینک‌های استفاده‌شده
#         file_search_call.results: نتایج جست‌وجو در فایل‌ها
#         code_interpreter_call.outputs: خروجی اجرای کد، مثل متن یا تصویر
#         computer_call_output.output.image_url: آدرس تصاویر ابزار کنترل کامپیوتر
#         message.input_image.image_url: آدرس تصاویر ورودی
#         message.output_text.logprobs: احتمال توکن‌های خروجی
#         reasoning.encrypted_content: reasoning رمزگذاری‌شده برای ادامهٔ مکالمه با store=False
#         response_include=None,   درخواست فیلدهای اضافی از Response
#         context_management=[ContextManagement(type="compaction", compact_threshold=10_000)],   فشرده‌سازی Context مکالمات بسیار طولانی در Providerهای پشتیبانی‌شده
#         prompt_cache_options=PromptCacheOptions(mode="implicit", ttl="30m"),   تنظیم Prompt Cache برای مدل‌های پشتیبانی‌شده
#         preserve_raw_usage=True,   نگهداری Usage خام Provider در ModelResponse.raw_usage
#         timeout=60,   حداکثر زمان هر تلاش برای فراخوانی مدل، برحسب ثانیه
#     )
