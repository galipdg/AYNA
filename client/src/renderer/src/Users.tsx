import { useEffect, useState, type FormEvent } from 'react'
import type { Account, CurrentUser, Role, UsersError } from '../../shared/api.ts'
import ApiTokens from './ApiTokens.tsx'
import { strings, usersErrorText as errorText } from './strings.ts'

interface Props {
  user: CurrentUser
  /** The server answered 401 (or the admin ended their own session): the login screen takes over. */
  onSessionEnded(): void
  /** The admin changed their own role; the rest of the client follows it. */
  onUserChanged(user: CurrentUser): void
  onClose(): void
}

type List =
  | { state: 'loading' }
  | { state: 'loaded'; users: Account[] }
  | { state: 'failed'; error: UsersError }

type Notice = { kind: 'ok' | 'error'; text: string }

const ROLES: Role[] = ['admin', 'tester']

/** Admin-only account management (#60, FR-39); a tester sees why they cannot use it (SC-03). */
export default function Users(props: Props) {
  if (props.user.role !== 'admin') return <AdminOnly onClose={props.onClose} />
  return <UserManagement {...props} />
}

function AdminOnly({ onClose }: { onClose(): void }) {
  return (
    <section className="card">
      <h2>{strings.usersTitle}</h2>
      <p className="error" role="alert">
        {strings.usersAdminOnly}
      </p>
      <div className="actions">
        <button type="button" onClick={onClose}>
          {strings.usersBack}
        </button>
      </div>
    </section>
  )
}

function UserManagement({ user: me, onSessionEnded, onUserChanged, onClose }: Props) {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [notice, setNotice] = useState<Notice>()
  const [busy, setBusy] = useState(false)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    let cancelled = false
    window.ayna.listUsers().then(
      (result) => !cancelled && showList(result),
      () => !cancelled && setList({ state: 'failed', error: { ok: false, reason: 'unreachable' } }),
    )
    return () => {
      cancelled = true
    }
    // `showList` only reads props that do not change while the screen is open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function showList(result: Awaited<ReturnType<typeof window.ayna.listUsers>>) {
    if (result.ok) return setList({ state: 'loaded', users: result.users })
    if (result.reason === 'unauthorized') return onSessionEnded()
    if (result.reason === 'forbidden') return setForbidden(true)
    setList({ state: 'failed', error: result })
  }

  function reload() {
    setList({ state: 'loading' })
    window.ayna
      .listUsers()
      .then(showList, () =>
        setList({ state: 'failed', error: { ok: false, reason: 'unreachable' } }),
      )
  }

  /**
   * Runs one change; on success applies it to the list and shows `done`. Returns whether it
   * succeeded, so a form can clear itself.
   */
  async function change<T extends { ok: true }>(
    call: () => Promise<T | UsersError>,
    apply: (result: T, users: Account[]) => Account[],
    done: (result: T) => string,
  ): Promise<boolean> {
    setBusy(true)
    setNotice(undefined)
    try {
      const result = await call()
      if (!result.ok) {
        if (result.reason === 'unauthorized') onSessionEnded()
        else if (result.reason === 'forbidden') setForbidden(true)
        else setNotice({ kind: 'error', text: errorText(result) })
        return false
      }
      setList((current) =>
        current.state === 'loaded'
          ? { state: 'loaded', users: apply(result, current.users) }
          : current,
      )
      setNotice({ kind: 'ok', text: done(result) })
      return true
    } catch {
      setNotice({ kind: 'error', text: strings.usersErrors.unreachable })
      return false
    } finally {
      setBusy(false)
    }
  }

  function replace(updated: Account) {
    return (users: Account[]) => users.map((u) => (u.id === updated.id ? updated : u))
  }

  async function setRole(account: Account, role: Role) {
    const ok = await change(
      () => window.ayna.updateUser(account.id, { role }),
      (result, users) => replace(result.user)(users),
      (result) => strings.roleChanged(result.user.username, strings.roles[result.user.role]),
    )
    if (ok && account.id === me.id) onUserChanged({ ...me, role })
  }

  async function setPassword(account: Account, password: string) {
    const ok = await change(
      () => window.ayna.updateUser(account.id, { password }),
      (result, users) => replace(result.user)(users),
      () => strings.passwordChanged(account.username),
    )
    // The server ended every session of that account, this one included.
    if (ok && account.id === me.id) onSessionEnded()
    return ok
  }

  async function remove(account: Account) {
    const ok = await change(
      () => window.ayna.removeUser(account.id),
      (_result, users) => users.filter((u) => u.id !== account.id),
      () => strings.userRemoved(account.username),
    )
    if (ok && account.id === me.id) onSessionEnded()
  }

  function create(username: string, password: string, role: Role) {
    return change(
      () => window.ayna.createUser(username, password, role),
      (result, users) =>
        [...users, result.user].sort((a, b) => a.username.localeCompare(b.username)),
      (result) => strings.userCreated(result.user.username),
    )
  }

  if (forbidden) return <AdminOnly onClose={onClose} />

  return (
    <section className="card">
      <h2>{strings.usersTitle}</h2>
      <p>{strings.usersIntro}</p>
      {/* Above the list, so the answer stays in view however long the list is. */}
      {notice && (
        <p className={notice.kind} role={notice.kind === 'error' ? 'alert' : 'status'}>
          {notice.text}
        </p>
      )}

      {list.state === 'loading' && <p>{strings.loading}</p>}
      {list.state === 'failed' && (
        <div className="actions">
          <p className="error" role="alert">
            {errorText(list.error)}
          </p>
          <button type="button" onClick={reload}>
            {strings.usersRetry}
          </button>
        </div>
      )}
      {list.state === 'loaded' && (
        <ul className="user-list">
          {list.users.map((account) => (
            <UserRow
              key={account.id}
              account={account}
              isMe={account.id === me.id}
              busy={busy}
              onRole={(role) => setRole(account, role)}
              onPassword={(password) => setPassword(account, password)}
              onRemove={() => remove(account)}
              onSessionEnded={onSessionEnded}
            />
          ))}
        </ul>
      )}

      <NewUser busy={busy} onCreate={create} />

      <div className="actions">
        <button type="button" onClick={onClose} disabled={busy}>
          {strings.usersBack}
        </button>
      </div>
    </section>
  )
}

interface RowProps {
  account: Account
  isMe: boolean
  busy: boolean
  onRole(role: Role): void
  onPassword(password: string): Promise<boolean>
  onRemove(): void
  onSessionEnded(): void
}

type Open = 'none' | 'password' | 'remove' | 'tokens'

function UserRow({ account, isMe, busy, onRole, onPassword, onRemove, onSessionEnded }: RowProps) {
  const [open, setOpen] = useState<Open>('none')
  const [password, setPasswordText] = useState('')
  const toggle = (next: Open) => setOpen(open === next ? 'none' : next)

  async function savePassword(event: FormEvent) {
    event.preventDefault()
    if (await onPassword(password)) {
      setPasswordText('')
      setOpen('none')
    }
  }

  const roleId = `role-${account.id}`
  const passwordId = `password-${account.id}`
  return (
    <li>
      <div className="user-row">
        <span>
          <strong>{account.username}</strong> {isMe && strings.you}{' '}
          <span className="muted">{strings.createdOn(account.createdAt.slice(0, 10))}</span>
        </span>
        <span className="actions">
          <label htmlFor={roleId} className="visually-hidden">
            {strings.roleLabel}
          </label>
          <select
            id={roleId}
            value={account.role}
            onChange={(event) => onRole(event.target.value as Role)}
            disabled={busy}
          >
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {strings.roles[role]}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => toggle('password')} disabled={busy}>
            {strings.setPassword}
          </button>
          <button type="button" onClick={() => toggle('tokens')} disabled={busy}>
            {strings.tokens}
          </button>
          <button type="button" onClick={() => toggle('remove')} disabled={busy}>
            {strings.removeUser}
          </button>
        </span>
      </div>

      {open === 'password' && (
        <form className="app-form" onSubmit={savePassword}>
          <label htmlFor={passwordId}>{strings.newPasswordLabel(account.username)}</label>
          <input
            id={passwordId}
            type="password"
            autoComplete="new-password"
            autoFocus
            value={password}
            onChange={(event) => setPasswordText(event.target.value)}
            disabled={busy}
          />
          <div className="actions">
            <button type="submit" disabled={busy || !password}>
              {strings.savePassword}
            </button>
            <button type="button" onClick={() => setOpen('none')} disabled={busy}>
              {strings.cancel}
            </button>
          </div>
        </form>
      )}
      {open === 'remove' && (
        <div className="actions">
          <p>{strings.confirmRemove(account.username)}</p>
          <button type="button" onClick={onRemove} disabled={busy}>
            {strings.confirmRemoveButton}
          </button>
          <button type="button" onClick={() => setOpen('none')} disabled={busy}>
            {strings.cancel}
          </button>
        </div>
      )}
      {open === 'tokens' && (
        <ApiTokens
          account={account}
          onSessionEnded={onSessionEnded}
          onClose={() => setOpen('none')}
        />
      )}
    </li>
  )
}

function NewUser({
  busy,
  onCreate,
}: {
  busy: boolean
  onCreate(username: string, password: string, role: Role): Promise<boolean>
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('tester')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (await onCreate(username, password, role)) {
      setUsername('')
      setPassword('')
      setRole('tester')
    }
  }

  return (
    <>
      <h3>{strings.newUserTitle}</h3>
      <p className="muted">{strings.newUserHint}</p>
      <form className="app-form" onSubmit={submit}>
        <label htmlFor="new-username">{strings.usernameLabel}</label>
        <input
          id="new-username"
          type="text"
          autoComplete="off"
          spellCheck={false}
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          disabled={busy}
        />
        <label htmlFor="new-password">{strings.passwordLabel}</label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={busy}
        />
        <label htmlFor="new-role">{strings.roleLabel}</label>
        <select
          id="new-role"
          value={role}
          onChange={(event) => setRole(event.target.value as Role)}
          disabled={busy}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {strings.roles[r]}
            </option>
          ))}
        </select>
        <div className="actions">
          <button type="submit" disabled={busy || !username.trim() || !password}>
            {strings.createUser}
          </button>
        </div>
      </form>
    </>
  )
}
