# Sci_O-RAN: pre-start admission для Prompt12 T2

Это **инженерный preflight до day-start**, а не исполнитель научного эксперимента.

## Состав

- `prestart_prompt12.yml` — Ansible playbook; выполняется на контроллере `coll.vntu.org`, проверяет `tb3-dell`.
- `prestart_guard.py` — исполняется на `tb3-dell` посредством Ansible `script` (временная копия).
- `test_prestart_guard.py` — локальные моделируемые тесты логики защитного скрипта.

## Размещение

Разместите файлы рядом друг с другом на **контроллере вне Git-репозитория**, например в `/home/khoshaba/sci-oran/prestart-guard/`. Так новый файл не сделает рабочее дерево авторитетного репозитория грязным.

## Вызов (пример структуры)

Замените `EXP_ID` и `RUN_ID` **новыми, ранее не потреблёнными** значениями; скрипт проверит их по настоящему штатному materializer. Не выбирайте исторический R05 повторно.

```bash
cd /home/khoshaba/sci-oran/prestart-guard
ansible-playbook \
  -i /home/khoshaba/project/tcd-oran-testbed-integration/sci-oran/ansible/inventory.ini \
  ./prestart_prompt12.yml \
  -e "experiment_id=EXP_ID" \
  -e "run_id=RUN_ID"
```

Проверка **сама выводит FIFO path из реального provider identity materializer**; вручную задавать FIFO не нужно.

## Условия PASS

- Рабочий каталог Git чист, ветка `main`, HEAD равен `approved_head`.
- Выбранные EXP/RUN ещё не заняты настоящими или архивными evidence и не конфликтуют с receiver container.
- На машине не работают четыре основных контейнера Tb3.
- Реальный штатный runtime-profile materializer принимает идентификаторы и создаёт корректную конфигурацию **в одноразовом временном каталоге**.
- Штатные production binding, precontrol resume и single T2 materializer проходят пробный запуск без научных действий.
- Provider identity согласована с derived runtime root/FIFO, provider-launch materializer выдаёт argv; argv **не выполняется**.

Любой отказ = `PRESTART_GATE=BLOCKED`, реальный day-start **не производить**. При `EXPERIMENT_ID_INVALID` скрипт возвращает эту причину.

## Ограничения

- На реальном Tb3 исполняемый preflight ещё не проверен: до применения требуется один авторизованный пробный запуск на остановленном тестбеде.
- Пробный прогон записывает файлы **только во временном каталоге системы**, затем удаляет их; он не изменяет evidence root, репозиторий, runtime root, provider или Docker-контейнеры.
- `approved_head` и `portable_admission` в playbook основаны на checkpoint 2026-10-08. При обновлении Git HEAD или admission оба значения необходимо обновить **после проверки происхождения**.
- Скрипт проверяет вызываемость отдельных non-executing materializer, но не полный live handoff, IP-связность 5G, состояние UE, фактическую стационарность или authoritative readback.
- Preflight **не встроен** в canonical lifecycle wrapper: он блокирует собственный playbook, но не запрещает кому-либо отдельно выполнить day-start. Для обязательного автоматического enforcement потребуется отдельное одобренное изменение Ansible lifecycle.
- Ни day-start, ни scientific traffic, ни PRB control этим кодом не авторизованы.

## Примечание к проверенной версии (2026-10-08)

Это кандидат для отдельной инженерной проверки, **не** подключённый к canonical lifecycle.
Изменения относительно прототипа:
- обязательная проверка, что все шесть `ratio_binding_paths` находятся внутри disposable sandbox, включая защиту от symlink escape и дублирования;
- три отрицательных unit-теста для путей;
- поле `ACTUAL_EVIDENCE_WRITE_REQUESTED=NO` вместо неподтверждённого утверждения `ACTUAL_EVIDENCE_MODIFIED=NO`.

Важные ограничения: эти тесты используют mocks; end-to-end materializer integration на опубликованном Tb3 HEAD не проведена. Не доказана полная изоляция сторонних файловых записей всех вызываемых materializer. `approved_head` следует указывать для действительно опубликованного commit; локальный непубликованный patch на `coll.vntu.org` не означает, что тот же код есть на `tb3-dell`. В текущем playbook `approved_head` фиксирован и требует обновления после разрешённой публикации. Запуск guard до sync соответствующего HEAD с `tb3-dell` недопустим.
