import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { notificationsApi } from '../api/client'
import toast from 'react-hot-toast'

interface NotificationSettings {
  email_enabled: boolean
  email_address: string
  webhook_url: string
}

export default function Settings() {
  const { user } = useAuth()
  const [notif, setNotif] = useState<NotificationSettings>({
    email_enabled: false,
    email_address: '',
    webhook_url: '',
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const fetchSettings = async () => {
      setLoading(true)
      try {
        const res = await notificationsApi.get()
        setNotif({
          email_enabled: res.data.email_enabled,
          email_address: res.data.email_address || '',
          webhook_url: res.data.webhook_url || '',
        })
      } catch {
        // default values
      } finally {
        setLoading(false)
      }
    }
    fetchSettings()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await notificationsApi.update(notif)
      toast.success('Settings saved')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Settings</h1>

      <div className="space-y-6 max-w-2xl">
        {/* Profile */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-200 mb-4">Profile</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">Name</label>
              <input
                type="text"
                value={user?.name || ''}
                disabled
                className="input-field opacity-60 cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">Email</label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="input-field opacity-60 cursor-not-allowed"
              />
            </div>
            <p className="text-xs text-gray-600">
              Profile editing coming soon
            </p>
          </div>
        </div>

        {/* Notifications */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-200 mb-4">Notifications</h2>
          {loading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-10 bg-dark-700 rounded" />
              <div className="h-10 bg-dark-700 rounded w-1/2" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-200">Email Notifications</p>
                  <p className="text-xs text-gray-500">Get notified when document processing completes</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notif.email_enabled}
                    onChange={(e) => setNotif({ ...notif, email_enabled: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-accent-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-600" />
                </label>
              </div>

              {notif.email_enabled && (
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">Email Address</label>
                  <input
                    type="email"
                    value={notif.email_address}
                    onChange={(e) => setNotif({ ...notif, email_address: e.target.value })}
                    className="input-field"
                    placeholder="notifications@example.com"
                  />
                </div>
              )}

              {/* Independent of the email toggle — webhooks work on their own */}
              <div className="pt-2 border-t border-dark-700">
                <label className="block text-sm font-medium text-gray-400 mb-1.5 mt-4">Webhook URL</label>
                <input
                  type="url"
                  value={notif.webhook_url}
                  onChange={(e) => setNotif({ ...notif, webhook_url: e.target.value })}
                  className="input-field"
                  placeholder="https://example.com/hooks/docprocess"
                />
                <p className="text-xs text-gray-500 mt-1.5">
                  POSTed on every processing completion (success and failure). Leave blank to disable.
                </p>
              </div>

              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
