import { useEffect, useState } from 'react'
import {
  RUN_STATUSES,
  type Application,
  type ReportResult,
  type RunFilter,
  type RunStatus,
  type RunsError,
  type RunSummary,
  type TestSummary,
} from '../../shared/api.ts'
import Page from './Page.tsx'
import { formatDate, formatDuration, formatTime, runsErrorText, strings } from './strings.ts'

interface Props {
  app: Application
  /** The server answered 401: the login screen takes over. */
  onSessionEnded(): void
}

/** What the server returns at most; at this count older runs may be hidden (#68). */
const LIMIT = 100

type List =
  | { state: 'loading' }
  | { state: 'loaded'; runs: RunSummary[] }
  | { state: 'failed'; error: RunsError }

/** A list and the request it answers; an older answer reads as still loading. */
type Answered = { key: string; list: List }

type Notice = { kind: 'ok' | 'error' | 'info'; text: string }

const PILL: Record<RunStatus, string> = {
  running: 'pill-accent',
  passed: 'pill-success',
  failed: 'pill-danger',
  aborted: 'pill-warning',
}

/** The run history (#68, FR-22): the application's runs, filtered by test and result. */
export default function Runs({ app, onSessionEnded }: Props) {
  const [filter, setFilter] = useState<RunFilter>({})
  const [tests, setTests] = useState<TestSummary[]>([])
  const [answered, setAnswered] = useState<Answered>({ key: '', list: { state: 'loading' } })
  const [notice, setNotice] = useState<Notice>()
  const [busy, setBusy] = useState<string>()
  const [reloads, setReloads] = useState(0)

  useEffect(() => {
    let cancelled = false
    window.ayna.listTests(app.id).then(
      (result) => {
        if (cancelled) return
        if (result.ok) setTests(result.tests)
        else if (result.reason === 'unauthorized') onSessionEnded()
      },
      () => {},
    )
    return () => {
      cancelled = true
    }
    // `onSessionEnded` does not change while the screen is open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.id, reloads])

  const key = JSON.stringify([app.id, filter, reloads])
  const list: List = answered.key === key ? answered.list : { state: 'loading' }

  useEffect(() => {
    let cancelled = false
    const setList = (next: List) => setAnswered({ key, list: next })
    window.ayna.listRuns(app.id, filter).then(
      (result) => {
        if (cancelled) return
        if (result.ok) return setList({ state: 'loaded', runs: result.runs })
        if (result.reason === 'unauthorized') return onSessionEnded()
        // The chosen test was deleted meanwhile: show every test again.
        if (result.reason === 'not-found' && filter.testId)
          return setFilter({ ...filter, testId: undefined })
        setList({ state: 'failed', error: result })
      },
      () => !cancelled && setList({ state: 'failed', error: { ok: false, reason: 'unreachable' } }),
    )
    return () => {
      cancelled = true
    }
    // `key` stands for app, filter and reloads; `onSessionEnded` does not change meanwhile.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const names = new Map(tests.map((test) => [test.id, test.name]))
  const testName = (run: RunSummary) => names.get(run.testId) ?? strings.runsUnknownTest

  async function report(run: RunSummary, save: boolean) {
    setBusy(run.id)
    setNotice(save ? undefined : { kind: 'info', text: strings.runsOpening })
    let result: ReportResult
    try {
      result = save
        ? await window.ayna.saveReport(run.id, fileName(testName(run), run.startedAt))
        : await window.ayna.openReport(run.id)
    } catch {
      result = { ok: false, reason: 'unreachable' }
    }
    setBusy(undefined)
    if (result.ok) {
      setNotice(result.path ? { kind: 'ok', text: strings.runsSaved(result.path) } : undefined)
    } else if (result.reason === 'unauthorized') {
      onSessionEnded()
    } else if (result.reason === 'cancelled') {
      setNotice(undefined)
    } else {
      setNotice({ kind: 'error', text: runsErrorText(result) })
    }
  }

  const sortedTests = [...tests].sort((a, b) => a.name.localeCompare(b.name, strings.locale))
  const filtered = Boolean(filter.testId || filter.status)

  return (
    <Page
      title={strings.nav.runs}
      help={strings.pageHelp.runs}
      actions={
        <button type="button" className="btn-quiet" onClick={() => setReloads((n) => n + 1)}>
          {strings.runsRefresh}
        </button>
      }
    >
      <div className="runs-filters">
        <label>
          <span>{strings.runsFilterTest}</span>
          <select
            value={filter.testId ?? ''}
            onChange={(event) => setFilter({ ...filter, testId: event.target.value || undefined })}
          >
            <option value="">{strings.runsAllTests}</option>
            {sortedTests.map((test) => (
              <option key={test.id} value={test.id}>
                {test.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>{strings.runsFilterStatus}</span>
          <select
            value={filter.status ?? ''}
            onChange={(event) =>
              setFilter({ ...filter, status: (event.target.value || undefined) as RunStatus })
            }
          >
            <option value="">{strings.runsAllStatuses}</option>
            {RUN_STATUSES.map((status) => (
              <option key={status} value={status}>
                {strings.runsStatus[status]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {notice && (
        <p
          className={`message message-${{ ok: 'success', error: 'danger', info: 'info' }[notice.kind]}`}
          role={notice.kind === 'error' ? 'alert' : 'status'}
        >
          {notice.text}
        </p>
      )}

      {list.state === 'loading' && <p className="hint">{strings.loading}</p>}
      {list.state === 'failed' && (
        <p className="message message-danger" role="alert">
          {runsErrorText(list.error)}{' '}
          <button type="button" className="btn-quiet" onClick={() => setReloads((n) => n + 1)}>
            {strings.runsRefresh}
          </button>
        </p>
      )}
      {list.state === 'loaded' && list.runs.length === 0 && (
        <div className="empty">
          <p className="empty-title">{filtered ? strings.runsNoMatch : strings.runsEmpty}</p>
          {!filtered && <p className="hint">{strings.runsEmptyHint}</p>}
        </div>
      )}
      {list.state === 'loaded' && list.runs.length > 0 && (
        <>
          <table className="runs-table">
            <thead>
              <tr>
                <th scope="col">{strings.runsHeaderTest}</th>
                <th scope="col">{strings.runsHeaderResult}</th>
                <th scope="col">{strings.runsHeaderStarted}</th>
                <th scope="col">{strings.runsHeaderDuration}</th>
                <th scope="col">{strings.runsHeaderBy}</th>
                <th scope="col">
                  <span className="visually-hidden">{strings.runsOpenReport}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.runs.map((run) => (
                <tr key={run.id} onDoubleClick={() => busy || report(run, false)}>
                  <td>
                    <span className="runs-test">{testName(run)}</span>
                    <span className="hint">{strings.runsSteps(run.stepCount)}</span>
                  </td>
                  <td>
                    <span className={`pill ${PILL[run.status]}`}>
                      <span className="dot" />
                      {strings.runsStatus[run.status]}
                    </span>
                  </td>
                  <td className="runs-number">
                    {formatDate(run.startedAt)} {formatTime(run.startedAt)}
                  </td>
                  <td className="runs-number">
                    {run.durationMs === null ? '–' : formatDuration(run.durationMs)}
                  </td>
                  <td>{run.startedBy}</td>
                  <td className="runs-actions">
                    {/* The cell stays a table cell, so its border lines up with the row's (#68). */}
                    <div className="actions">
                      <button
                        type="button"
                        disabled={Boolean(busy)}
                        onClick={() => report(run, false)}
                      >
                        {strings.runsOpenReport}
                      </button>
                      <button
                        type="button"
                        className="btn-quiet"
                        disabled={Boolean(busy)}
                        title={strings.runsSaveReportTitle(testName(run))}
                        onClick={() => report(run, true)}
                      >
                        {strings.runsSaveReport}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {list.runs.length >= LIMIT && <p className="hint">{strings.runsLimit(LIMIT)}</p>}
        </>
      )}
    </Page>
  )
}

/** "AYNA Giriş 2026-11-10 15-04": the test and the local start time, safe in a file name. */
function fileName(test: string, startedAt: string): string {
  const date = new Date(startedAt)
  if (Number.isNaN(date.getTime())) return `AYNA ${test}`
  const pad = (n: number) => String(n).padStart(2, '0')
  const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  return `AYNA ${test} ${day} ${pad(date.getHours())}-${pad(date.getMinutes())}`
}
