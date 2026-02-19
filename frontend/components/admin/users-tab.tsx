'use client';

import { useState } from 'react';
import {
  useAdminUsers,
  useCreateUser,
  useUpdateUser,
  type AdminUser,
} from '@/hooks/use-admin';
import { Users, UserPlus, Mail, Lock, Shield, Clock, Trash2, Power } from 'lucide-react';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function RoleBadge({ role }: { role: string }) {
  const isAdmin = role === 'admin';
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        isAdmin
          ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
      }`}
    >
      {role}
    </span>
  );
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
      active
        ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
        : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
    }`}>
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

/* ── Mobile card for a single user ── */
function UserCard({ user }: { user: AdminUser }) {
  const updateUser = useUpdateUser();

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 min-w-0 overflow-hidden">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
              <Users className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {user.username}
                </span>
                <RoleBadge role={user.role} />
              </div>
              {user.full_name && (
                <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user.full_name}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 flex-wrap min-w-0">
        <div className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500 truncate">
          <Clock className="h-3 w-3 shrink-0" />
          <span className="truncate">{formatDate(user.last_login)}</span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => updateUser.mutate({ userId: user.id, is_active: !user.is_active })}
            disabled={updateUser.isPending}
            className={`flex items-center gap-1 rounded px-1.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 whitespace-nowrap ${
              user.is_active
                ? 'bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400'
                : 'bg-green-50 text-green-600 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400'
            }`}
          >
            <Power className="h-3 w-3" />
            {user.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Desktop table row ── */
function UserRow({ user }: { user: AdminUser }) {
  const updateUser = useUpdateUser();

  return (
    <tr className="border-b border-gray-200 dark:border-gray-700 last:border-b-0">
      <td className="px-3 py-2 text-sm text-gray-900 dark:text-white">{user.username}</td>
      <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-300">{user.full_name || '-'}</td>
      <td className="px-3 py-2"><RoleBadge role={user.role} /></td>
      <td className="px-3 py-2"><StatusDot active={user.is_active} /></td>
      <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">{formatDate(user.last_login)}</td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => updateUser.mutate({ userId: user.id, is_active: !user.is_active })}
            disabled={updateUser.isPending}
            className={`rounded px-2 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
              user.is_active
                ? 'bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400'
                : 'bg-green-50 text-green-600 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400'
            }`}
          >
            {user.is_active ? 'Deactivate' : 'Activate'}
          </button>
          <select
            value={user.role}
            onChange={(e) => updateUser.mutate({ userId: user.id, role: e.target.value })}
            disabled={updateUser.isPending}
            className="rounded border border-gray-200 bg-white px-1.5 py-1 text-xs text-gray-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 disabled:opacity-50"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </div>
      </td>
    </tr>
  );
}

function CreateUserForm({ onClose }: { onClose: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('user');
  const [error, setError] = useState('');
  const createUser = useCreateUser();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password.trim()) {
      setError('Username and password are required.');
      return;
    }
    createUser.mutate(
      {
        username: username.trim(),
        password: password.trim(),
        full_name: fullName.trim() || undefined,
        role,
      },
      {
        onSuccess: () => {
          setUsername('');
          setPassword('');
          setFullName('');
          setRole('user');
          onClose();
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : 'Failed to create user.');
        },
      }
    );
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/50 overflow-hidden"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 min-w-0">
        <div>
          <label className="flex items-center gap-1 mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
            <Users className="h-3 w-3" />
            Username *
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
            className="w-full min-w-0 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-900 placeholder-gray-400 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500"
          />
        </div>
        <div>
          <label className="flex items-center gap-1 mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
            <Lock className="h-3 w-3" />
            Password *
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="password"
            className="w-full min-w-0 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-900 placeholder-gray-400 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500"
          />
        </div>
        <div>
          <label className="flex items-center gap-1 mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
            <Mail className="h-3 w-3" />
            Full Name
          </label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="optional"
            className="w-full min-w-0 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-900 placeholder-gray-400 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500"
          />
        </div>
        <div>
          <label className="flex items-center gap-1 mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
            <Shield className="h-3 w-3" />
            Role
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full min-w-0 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </div>
      </div>
      {error && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
      <div className="mt-3 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={createUser.isPending}
          className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {createUser.isPending ? 'Creating...' : 'Create User'}
        </button>
      </div>
    </form>
  );
}

export default function UsersTab() {
  const { data: users, isLoading, error } = useAdminUsers();
  const [showForm, setShowForm] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-gray-500 dark:text-gray-400">
        Loading users...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
        Failed to load users: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    );
  }

  return (
    <div className="min-w-0 overflow-x-hidden">
      <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Users ({users?.length ?? 0})
          </h3>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary/90 transition-colors"
        >
          {showForm ? (
            <>Cancel</>
          ) : (
            <>
              <UserPlus className="h-3 w-3" />
              Create User
            </>
          )}
        </button>
      </div>

      {showForm && (
        <div className="mb-3">
          <CreateUserForm onClose={() => setShowForm(false)} />
        </div>
      )}

      {!users || users.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-600 py-6 text-center text-sm text-gray-400 dark:text-gray-500">
          No users found.
        </div>
      ) : (
        <>
          {/* Mobile: card layout */}
          <div className="sm:hidden space-y-2">
            {users.map((user) => (
              <UserCard key={user.id} user={user} />
            ))}
          </div>

          {/* Desktop: table layout */}
          <div className="hidden sm:block overflow-x-auto rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/80">
                  <th className="px-3 py-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Username</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Full Name</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Role</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Status</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Last Login</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <UserRow key={user.id} user={user} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
