# f_brain - Project Notes

## Project Vision

*What is this project? Why does it exist? Who is it for?*

---

## Session Notes

### [2026-02-17] Initial Setup
- Frame project initialized

### [2026-02-17] Architecture: Universal LLM Provider Router

**Проблема:** f_brain жёстко привязан к Claude CLI — все три метода `ClaudeProcessor` вызывают `subprocess.run(["claude", ...])`. Невозможно использовать другие LLM-провайдеры.

**Решение:** Создаём пакет `src/d_brain/llm/` с абстракцией и двумя реализациями.

**Архитектурные решения:**
- Claude CLI остаётся как есть — MCP работает из коробки, ломать незачем
- OpenAI через SDK с function calling — `TodoistToolExecutor` вызывает Todoist API напрямую
- `openai_base_url` даёт совместимость с Ollama, Together и другими OpenAI-compatible API
- Промпты не трогаем на первом этапе — MCP-инструкции OpenAI проигнорирует
- Провайдер выбирается через `LLM_PROVIDER=claude-cli|openai` в `.env`

**Структура нового пакета:**
```
src/d_brain/llm/
    __init__.py      # экспорт
    base.py          # ABC LLMProvider + dataclasses (LLMResponse, ToolDefinition, ToolCall)
    claude_cli.py    # ClaudeCLIProvider — subprocess логика из processor.py
    openai_api.py    # OpenAIProvider — openai SDK + function calling + tool loop
    tools.py         # ToolDefinition для Todoist + TodoistToolExecutor
    router.py        # get_provider() — фабрика по имени из конфига
```

**Изменяемые файлы:**
- `config.py` — +4 поля: `llm_provider`, `openai_api_key`, `openai_model`, `openai_base_url`
- `processor.py` — `ClaudeProcessor` → `LLMProcessor`, методы async, принимает `LLMProvider`
- `handlers/process.py`, `do.py`, `weekly.py` — фабрика `create_processor()`, убираем `asyncio.to_thread`
- `pyproject.toml` — +`openai` dependency

**Ключевая абстракция:**
```python
class LLMProvider(ABC):
    async def execute(self, prompt: str, *, tools: list[ToolDefinition] | None = None, timeout: int = 1200) -> LLMResponse: ...
```

**Объём:** ~400 строк нового кода, ~100 строк изменений. 6 новых файлов, 6 изменяемых.

### [2026-02-17] Documentation Update Before Change Planning
User: актуалиизруй пока документацию поп роекту. Делать план будем после этого

User: goals ведь надо будет создать? или нет?

Assistant: С нуля создавать не нужно: шаблоны уже есть в `vault/goals/` (`0-vision-3y.md`, `1-yearly-2025.md`, `2-monthly.md`, `3-weekly.md`). Нужно просто заполнить их под себя; отдельный `1-yearly-2026.md` создавать только если хочешь вести новый год отдельным файлом.

Assistant: Я выделил это как task по правилам Frame. Добавить запись в `tasks.json`? И отдельно: добавить этот контекст в `PROJECT_NOTES.md`?

User: да. да
