# Full example

These English and Russian examples are synthetic instructional illustrations. Their names, dates, quantities, and claims are supplied as example input, not verified reports about real products. They illustrate filler removal and informative recomposition, not detector performance or a calibrated quality score. Legitimate punctuation, complete three-item lists, and similar sentence lengths may remain. The goal is to improve the supplied prose in its own language and register, without a texture quota.

**Preservation takes precedence over every style pattern.** Preserve substantive claims, attribution, uncertainty, numbers, dates, units, limits, logical relationships, and every enumeration member. Remove only content-free filler, redundant restatement, and chatbot scaffolding unless the user requests abridgment. Keep protected content and the requested editing scope unchanged.

## Example 1: English project update

**Before:**
> Great question! Here is the project update.
>
> It's important to note that the team's 12 May 2026 pilot report says the revised dashboard may reduce the time staff spend finding reports. The finding is limited to the pilot group, and the report does not establish whether the benefit will persist.
>
> The pilot covered three workflows: exporting reports, comparing monthly totals, and checking access permissions. Additionally, the team has not yet measured error rates. For the pilot, the system allowed at most 20 exports per user per day.
>
> In conclusion, the team will review the pilot on 30 June 2026. Let me know if you'd like more detail!

**Content Intelligence scan:**
- Language: English.
- Content type: Project update with a neutral, factual register.
- Mixed content: None.
- Voice signals: The conversational wrapper does not authorize adding opinions or personal experience to the body.
- Editing targets: “It's important to note,” “Additionally,” and the chatbot wrapper delay an otherwise direct update without adding information. The report's attribution and limitations carry information.
- Paragraph review: The paragraphs cover the qualified finding, pilot scope and limits, and next review. Their order and repeated references to the pilot make the relationships clear; no structural variation is required.

**Self-audit Pass 1 - questions to ask of a draft:**
- Does “may reduce” remain uncertain, rather than becoming “reduces”?
- Are the pilot-group limitation and the unknown persistence of the benefit still present?
- Are all three workflows present?
- Does the export limit still apply per user, per day, and only to the pilot?
- Have the dates, the unmeasured error rates, and the planned review survived?

**Final rewrite:**
> The team's 12 May 2026 pilot report says the revised dashboard may reduce the time staff spend finding reports. The finding is limited to the pilot group, and the report does not establish whether the benefit will persist.
>
> The pilot covered exporting reports, comparing monthly totals, and checking access permissions. The team has not yet measured error rates. For the pilot, the system allowed at most 20 exports per user per day.
>
> The team will review the pilot on 30 June 2026.

**Content preservation check:**
| Supplied content | Where it survives |
|------------------|-------------------|
| Team's report and 12 May 2026 date | Opening sentence |
| Revised dashboard may reduce report-finding time | Opening sentence, with “may” retained |
| Finding limited to pilot group; persistence not established | Second sentence |
| Exporting reports, comparing monthly totals, checking access permissions | Complete enumeration in second paragraph |
| Error rates not yet measured by the team | Second paragraph |
| At most 20 exports per user per day during the pilot | Second paragraph, with all units and limits |
| Team will review pilot on 30 June 2026 | Final paragraph |

**Quality review (instructional):**
- The rewrite states the update directly and keeps its neutral register.
- The final paragraph stays because it contains a planned action and date; its position does not make it disposable.
- The three-item enumeration stays complete. No click counts, new sources, or claims of proven benefit appear.

**Changes made:**
- Removed “Great question,” the introductory wrapper, and the offer to continue.
- Removed “It's important to note,” “Additionally,” and “In conclusion.”
- Removed “three workflows” as a redundant introduction while preserving all three workflows.

**Verification status:** This is a supplied-input comparison for an instructional example. No independent judge result, detector result, or numerical quality score is claimed.

---

## Example 2: Russian technical documentation, with code

**Before:**
> ## Начало Работы
>
> Важно отметить, что Atlas — библиотека для синхронизации состояния через WebSocket. Согласно руководству команды от 12 мая 2026 года, библиотека может уменьшить задержку синхронизации в локальной сети; для мобильных сетей это пока не проверено.
>
> Для начала работы необходимо сначала установить пакет, а затем настроить сервер. Следует помнить, что для настройки нужны адрес сервера, ключ доступа и имя канала.
>
> ```bash
> npm install atlas-sync
> ```
>
> Крайне важно подчеркнуть, что время ожидания — 30 секунд. По достижении лимита запрос завершается ошибкой; автоматический повтор не предусмотрен.
>
> В заключение необходимо отметить, что руководство пока не описывает восстановление соединения.

**Content Intelligence scan:**
- Language: Russian, with a product name, protocol name, and protected shell command.
- Content type: Technical documentation with a neutral register.
- Mixed content: Heading and fenced code block; preserve the code exactly.
- Voice signals: No personal opinions or experience to amplify.
- Editing targets: “Важно отметить,” “Следует помнить,” and “Крайне важно подчеркнуть” repeat empty importance markers around straightforward documentation. The attribution, caveat, setup requirements, sequence, timeout, and recovery limitation carry information.
- Paragraph review: Keep the capability and its caveat together, the setup requirements beside the command, and the timeout beside the failure behavior. The final documentation limitation has a distinct purpose and stays.

**Final rewrite:**
> ## Начало работы
>
> Atlas — библиотека для синхронизации состояния через WebSocket. Согласно руководству команды от 12 мая 2026 года, библиотека может уменьшить задержку синхронизации в локальной сети; для мобильных сетей это пока не проверено.
>
> Сначала установите пакет, затем настройте сервер. Для настройки нужны адрес сервера, ключ доступа и имя канала.
>
> ```bash
> npm install atlas-sync
> ```
>
> Время ожидания — 30 секунд. По достижении лимита запрос завершается ошибкой; автоматический повтор не предусмотрен.
>
> Руководство пока не описывает восстановление соединения.

**Content preservation check:**
| Supplied content | Where it survives |
|------------------|-------------------|
| Atlas synchronizes state through WebSocket | Opening sentence |
| Team guide dated 12 мая 2026 года | Second sentence |
| Possible latency reduction in a local network | “может уменьшить” and “в локальной сети” retained |
| Mobile networks have not yet been checked | Caveat retained in the same sentence |
| Install package before configuring server | “Сначала … затем” preserves order |
| Server address, access key, channel name | Complete three-item requirement |
| Installation command | Fenced code block unchanged |
| 30-second timeout and error at the limit | Timeout paragraph |
| No automatic retry | “автоматический повтор не предусмотрен” retained |
| Guide does not yet describe reconnection | Final sentence |

**Changes made:**
- Removed repeated importance markers and the formulaic conclusion opener.
- Shortened the setup instruction without changing its order or required inputs.
- Changed the heading to sentence case.
- Kept the grammatical Russian dashes in “Atlas — библиотека” and “Время ожидания — 30 секунд.” Their presence is not a style failure.
- Preserved the entire enumeration, qualifications, date, units, failure behavior, and code block.

**Verification status:** This is a supplied-input comparison for an instructional example. No API documentation coverage, product capability, independent judge score, or detector outcome is inferred beyond the supplied input. Russian detector performance remains unmeasured.

---

## Example 3: English full rewrite without filler

**Request:** Rewrite the full notice in natural, neutral prose; preserve all information.

**Before:**
> The nursery's seed orders close on 14 February. Orders may be collected from 3 March. Collection is available on weekdays between 09:00 and 16:00. The order form must include the seed variety and quantity. The nursery confirms stock before requesting payment. A confirmation does not reserve seeds beyond 48 hours. Orders that remain unpaid after that period are cancelled. Staff have not yet measured how often the deadline causes cancellations.

**After:**
> Seed orders for the nursery close on 14 February; the form must specify the variety and quantity. Collection is available from 3 March, on weekdays between 09:00 and 16:00.
>
> Before requesting payment, the nursery confirms stock. Confirmation does not reserve seeds beyond 48 hours, and orders still unpaid after that period are cancelled. Staff have not yet measured how often this deadline leads to cancellations.

The rewrite groups placing and collecting an order separately from confirmation and payment. It combines related facts instead of substituting synonyms sentence by sentence. The deadline, collection window, both form fields, stock-before-payment sequence, reservation limit, cancellation condition and unmeasured frequency all survive. It does not promise that confirmation guarantees stock throughout the 48 hours, or identify who cancels orders when the source leaves that actor unspecified. Neutral voice does not require retaining eight separate sentence frames. No particular paragraph or sentence count is the target.

**Same source, narrower request:** Under an explicit “Tier 1 only” request, the original notice can remain unchanged: its short factual sentences carry no actionable Tier 1 problem. A generic light pass permits local fixes across the catalog but no broader recomposition. Under “rewrite only the collection details,” only the two collection sentences are editable; the ordering, form, stock, payment and measurement sentences stay exact. Full-rewrite permission does not carry over to these narrower requests.

## Example 4: Russian full rewrite without added voice

**Запрос:** Полностью переработай формулировки, сохрани нейтральный стиль и все сведения.

**До:**
> В учебном центре заявления на вечерний курс принимают до 18 августа. Занятия начнутся 2 сентября. Они будут проходить по вторникам и четвергам с 19:00 до 20:30. Для записи нужны анкета и копия документа об образовании. Администратор проверяет комплектность документов, затем отправляет приглашение на собеседование. Приглашение не означает зачисления. Решение о зачислении принимает комиссия после собеседования. Центр пока не оценивал, помогает ли собеседование точнее распределять участников по группам.

**После:**
> Для записи на вечерний курс в учебном центре нужны анкета и копия документа об образовании. Заявления принимают до 18 августа. Занятия начнутся 2 сентября и будут проходить по вторникам и четвергам с 19:00 до 20:30.
>
> Администратор сначала проверяет комплектность документов и затем отправляет приглашение на собеседование. Само приглашение не означает зачисления: это решение комиссия принимает после собеседования. Центр пока не оценивал, помогает ли собеседование точнее распределять участников по группам.

Здесь условия подачи и расписание отделены от процедуры принятия решения. Сохранены обе части комплекта, даты, дни и время, обязанности администратора, порядок проверки и приглашения, оговорка о зачислении, роль комиссии и отсутствие оценки результата собеседования. Перестройка не добавляет рассказчика, мнения или гарантии зачисления; «после собеседования» по-прежнему относится к решению комиссии. Это пример редакторского выбора, а не измеренный результат детектора.

## Example 5: Supplied style without borrowed experience

**Request:** Fully rewrite the note using compatible features of the supplied sample. The sample provides style only.

**Style sample:** “Let's check the logs first. I tried that yesterday, and it helped.”

**Source:** “The team's next step is to compare the logs before deciding whether to expand the trial. The team has not set a decision date.”

**Rewrite:** “The team needs to compare the logs before deciding whether to expand the trial. The team hasn't set a decision date yet.”

The sample supports direct syntax and a conversational contraction. It does not supply yesterday's experience, a proven benefit or a first-person speaker for this note. The team's action, dependency and unset date survive. Without a sample, the source's neutral register is sufficient; no invented persona or request for samples is needed.

**Legitimate English control, unchanged:** “The analysis uses robust regression. However, rural clinics were excluded, so the estimate may not apply to them.” The technical term, meaningful contrast and qualified scope all belong. Similarly, “A wide range of temperatures” cannot automatically become “many temperatures,” and “At the end of the day, lock the door” must retain its timing when meant literally.

## Example 6: Mixed prose and precise paste cleanup

**Request:** Rewrite the introduction only. The first two lines are unwanted assistant/interface residue and may also be removed. Keep the reference section exact; do not translate.

**Before:**
> Certainly! Here is your note.
> Copy response
>
> ## Introduction
> It is important to note that the result may change. Статус — предварительный. See [guide](https://example.org/guide?utm_source=mail&x=1). citeunknown7
>
> ## Reference
> The literal token `citeturn0search0` is an example. Keep 👩‍💻 and café.

**After:**
>
> ## Introduction
> The result may change. Статус — предварительный. See [guide](https://example.org/guide?utm_source=mail&x=1). citeunknown7
>
> ## Reference
> The literal token `citeturn0search0` is an example. Keep 👩‍💻 and café.

Only explicitly unwanted residue and empty framing disappear. The blank line after the two removed lines remains outside the editable section. The unresolved citation remains because its appearance does not establish that it is disposable. The URL parameters, quoted token, emoji/joiner, accented text, grammatical Russian dash and out-of-scope section stay exact. No global Unicode cleanup or translation is justified.

## Grammatical prose with a structural objective

These are instructional examples, not pilot results or detector evidence. The objective is to connect the decision with its reason while retaining all qualifications.

**Source:** “The council should keep evening access. Evening access matters to residents who finish work after six. The current budget could cover one evening each week. It could not cover two. That estimate assumes volunteer support. Without volunteers, even one evening would require more funding.”

**Rewrite:** “The council should keep evening access for residents who finish work after six. If volunteers help, the current budget could cover one evening a week, but not two. Without volunteers, even one evening would require more funding.”

Preserved: the recommendation, affected residents/time, budget possibility, one-versus-two limit and volunteer-dependent estimate. “Could cover” cannot become “will cover,” and the last qualification cannot be dropped as a repetitive conclusion. No personal anecdote or stronger promise is added.

**Русский исходник:** «Библиотеке стоит сохранить вечерние часы. Они нужны жителям, которые заканчивают работу после шести. По предварительной оценке, нынешнего бюджета может хватить на один вечер в неделю, но не на два. Эта оценка предполагает помощь волонтёров. Без них даже один вечер потребует дополнительного финансирования».

**Редакция:** «Библиотеке стоит сохранить вечерние часы: они нужны жителям, которые заканчивают работу после шести. По предварительной оценке, если помогут волонтёры, нынешнего бюджета может хватить на один вечер в неделю, но не на два. Без волонтёров даже один вечер потребует дополнительного финансирования».

The recommendation, residents' need, preliminary estimate, possibility and condition remain attached to the same claims. A grammatical dash, technical term or repeated “волонтёры” would not itself justify another edit.

**Legitimate regularity:** “Back up the database. Verify the backup. Record the verification result.” These parallel instructions encode a useful order. Keep them unless the actual request provides a reader-facing reason to change their expression; a repeated imperative shape is not a failed objective.


## Contextual fidelity examples

These are instructional comparisons, not model trials or adjudicated evaluation labels. Review the entire passage before a verdict.

- “Her growing unease makes her more than an illustration of the premise” retains a causal relationship. “She grows uneasy and becomes more than an illustration” may leave only sequence; the reviewer must check whether the surrounding text supplies the original cause. Repeating both nouns is insufficient.
- «Фильм не пытается подробно объяснить устройство города» concerns intent. «Фильм не объясняет подробно устройство города» alone can lose that distinction. A source-only anchor asks whether this is intent or outcome; it supplies no preparatory paraphrase as an answer.
- «Улицы выглядят обещанием спокойствия» and «улицы обещают спокойствие» can preserve an impression within a metaphor and subsequent contrast. The shorter phrase is not automatically a certainty error. If the complete context leaves equivalence unclear, report the specific uncertainty; do not treat this disputed phrase as a mandatory negative example.

A valid report may contain minor findings from either tier and still PASS. A concrete substantial problem yields REVISE even with maximum requested scores. UNCERTAIN yields UNRESOLVED unless a demonstrated semantic FAIL already requires REVISE. Scores are normally NOT_REQUESTED; none of these examples establishes a detector outcome.
