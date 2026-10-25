from sys import stdin


def _configure_stdin() -> None:
    if hasattr(stdin, "reconfigure"):
        stdin.reconfigure(encoding="utf-8")


def _read_prompt() -> str:
    # prompt = input("\nTask: ").strip()
    # prompt = "یک پروژه کامل پایتونی برام بساز که درخواست کاربر را در گوگل سرچ کند ونتایج سرچ را در دیتابی ذخیره کن. به صورت ریکوئست به خود سایت گوگل باشد نه api سفارشی گوگل"
    prompt = "ادامه بده"
    if not prompt:
        raise SystemExit("Task cannot be empty.")
    return prompt


def read_user_input() -> str:
    _configure_stdin()
    return _read_prompt()
