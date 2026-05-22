"""
CLI-утилита для маскировки чувствительных данных в файлах (JSON/YAML)
и проверки наличия таких данных.
"""

import argparse
import json
import sys
import yaml

from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union

from maskinfly import Masker, AuditLogger
from maskinfly.utils import SENSITIVE_VAR_NAMES
from maskinfly.patterns import PATTERNS

# Попытка импорта YAML (опционально)
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_data(file_path: Path) -> Any:
    """Загружает данные из JSON или YAML файла в зависимости от расширения."""
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix.lower() in (".yaml", ".yml"):
            if not HAS_YAML:
                raise ImportError(
                    "PyYAML не установлен. Установите его через 'pip install pyyaml' или используйте JSON."
                )
            return yaml.safe_load(f)
        else:
            return json.load(f)


def dump_data(data: Any, file_path: Optional[Path], input_format: str) -> None:
    """Сохраняет данные в файл или stdout в исходном формате."""
    output = None
    if file_path:
        output = open(file_path, "w", encoding="utf-8")
    else:
        output = sys.stdout

    try:
        if input_format == "yaml":
            if not HAS_YAML:
                raise ImportError("PyYAML не установлен")
            yaml.dump(data, output, default_flow_style=False, allow_unicode=True)
        else:
            json.dump(data, output, indent=2, ensure_ascii=False)
            output.write("\n")
    finally:
        if file_path and output:
            output.close()


def build_masker(args: argparse.Namespace) -> Masker:
    kwargs = {
        "audit_enabled": args.audit,
        "deep_mask": args.deep_mask,
        "auto_varname": False,
    }
    # Передаём только явно заданные параметры (отличающиеся от значений по умолчанию)
    if args.mask_char != '*':
        kwargs["mask_char"] = args.mask_char
    if args.mask_length != 3:
        kwargs["mask_length"] = args.mask_length

    if args.config:
        masker = Masker.from_config(str(args.config), **kwargs)
    else:
        masker = Masker(**kwargs)
    return masker


def mask_command(args: argparse.Namespace) -> int:
    """Выполняет команду 'mask'."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Ошибка: файл {args.input} не найден.", file=sys.stderr)
        return 1

    try:
        data = load_data(input_path)
    except Exception as e:
        print(f"Ошибка загрузки файла: {e}", file=sys.stderr)
        return 1

    masker = build_masker(args)
    try:
        masked_data = masker.mask(data)
    except Exception as e:
        print(f"Ошибка маскировки: {e}", file=sys.stderr)
        return 1

    # Определяем формат вывода (по расширению выходного файла или входного)
    if args.output:
        out_path = Path(args.output)
        out_format = "yaml" if out_path.suffix.lower() in (".yaml", ".yml") else "json"
    else:
        out_format = "yaml" if input_path.suffix.lower() in (".yaml", ".yml") else "json"

    try:
        dump_data(masked_data, args.output and Path(args.output), out_format)
    except Exception as e:
        print(f"Ошибка сохранения: {e}", file=sys.stderr)
        return 1

    if args.audit:
        print("Аудит включён. Сообщения выводятся в stderr.", file=sys.stderr)

    return 0

def scan_sensitive(data: Any, path: str = "", results: Optional[List[Dict]] = None) -> List[Dict]:
    """
    Рекурсивно сканирует данные на наличие чувствительных паттернов и ключей.
    Возвращает список словарей: {path, type, reason, sample?}
    """
    if results is None:
        results = []

    # Обработка строк
    if isinstance(data, str):
        for pattern_name, (regex, _) in PATTERNS.items():
            if regex.search(data):
                results.append({
                    "path": path or "<root>",
                    "type": "string",
                    "reason": f"pattern:{pattern_name}",
                    "sample": data[:50] + ("..." if len(data) > 50 else "")
                })
                return results
        return results

    # Обработка словаря
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            if key.lower() in SENSITIVE_VAR_NAMES:
                results.append({
                    "path": new_path,
                    "type": "key",
                    "reason": "sensitive_key",
                    "sample": str(value)[:50] if value is not None else None
                })
            scan_sensitive(value, new_path, results)
        return results

    # Обработка списков/кортежей
    if isinstance(data, (list, tuple)):
        for idx, item in enumerate(data):
            new_path = f"{path}[{idx}]" if path else f"[{idx}]"
            scan_sensitive(item, new_path, results)
        return results

    return results

def check_command(args: argparse.Namespace) -> int:
    """Выполняет команду 'check' – сканирует файл на чувствительные данные."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Ошибка: файл {args.input} не найден.", file=sys.stderr)
        return 1

    try:
        data = load_data(input_path)
    except Exception as e:
        print(f"Ошибка загрузки файла: {e}", file=sys.stderr)
        return 1

    results = scan_sensitive(data)

    if not results:
        print("Чувствительные данные не обнаружены.")
        return 0

    # Форматируем вывод
    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("Найдены потенциально чувствительные данные:")
        for r in results:
            sample_str = f" (пример: {r['sample']})" if r.get("sample") else ""
            print(f"  - Путь: {r['path']}")
            print(f"    Тип: {r['type']}, причина: {r['reason']}{sample_str}")
            print()
    return 1  # код возврата 1, если что-то найдено


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="maskify",
        description="Маскировка чувствительных данных в JSON/YAML файлах и проверка наличия таких данных."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Доступные команды")

    # Подкоманда mask
    mask_parser = subparsers.add_parser("mask", help="Маскировать данные в файле")
    mask_parser.add_argument("input", help="Путь к входному файлу (JSON или YAML)")
    mask_parser.add_argument("-o", "--output", help="Путь к выходному файлу (если не указан, вывод в stdout)")
    mask_parser.add_argument("--audit", action="store_true", help="Включить аудит (логи в stderr)")
    mask_parser.add_argument("--config", help="Путь к JSON/YAML конфигурации для Masker")
    mask_parser.add_argument("--mask-char", default="*", help="Символ маски (по умолчанию '*')")
    mask_parser.add_argument("--mask-length", type=int, default=3, help="Длина маски (по умолчанию 3)")
    mask_parser.add_argument("--deep-mask", action="store_true", help="Рекурсивно маскировать внутри чувствительных ключей")
    mask_parser.set_defaults(func=mask_command)

    # Подкоманда check
    check_parser = subparsers.add_parser("check", help="Проверить наличие чувствительных данных без маскировки")
    check_parser.add_argument("input", help="Путь к входному файлу (JSON или YAML)")
    check_parser.add_argument("--format", choices=["text", "json"], default="text", help="Формат вывода отчёта")
    check_parser.set_defaults(func=check_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
