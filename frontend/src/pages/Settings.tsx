import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  notificationsApi,
  llmSettingsApi,
  LLM_PROVIDER_PRESETS,
  LLM_PROVIDER_LABELS,
  LLMProvider,
  LLMSettings,
} from '../api/client'
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

  // AI Provider
  const [llm, setLlm] = useState<LLMSettings>({
    provider: 'openai',
    base_url: LLM_PROVIDER_PRESETS.openai.base_url,
    model: LLM_PROVIDER_PRESETS.openai.model,
    has_api_key: false,
  })
  const [apiKey, setApiKey] = useState('')
  const [llmLoading, setLlmLoading] = useState(false)
  const [llmSaving, setLlmSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

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
    const fetchLlm = async () => {
      setLlmLoading(true)
      try {
        const res = await llmSettingsApi.get()
        setLlm(res.data)
      } catch {
        // defaults
      } finally {
        setLlmLoading(false)
      }
    }
    fetchSettings()
    fetchLlm()
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

  const handleProviderChange = (provider: LLMProvider) => {
    const preset = LLM_PROVIDER_PRESETS[provider]
    setLlm((prev) => ({
      ...prev,
      provider,
      base_url: preset.base_url,
      model: preset.model,
    }))
  }

  const handleLlmSave = async () => {
    setLlmSaving(true)
    try {
      const payload: {
        provider: LLMProvider
        base_url: string
        model: string
        api_key?: string
      } = {
        provider: llm.provider,
        base_url: llm.base_url,
        model: llm.model,
      }
      // Only send the key when the user typed a new one — an absent key keeps the stored one.
      if (apiKey.trim()) {
        payload.api_key = apiKey.trim()
      }
      const res = await llmSettingsApi.update(payload)
      setLlm(res.data)
      setApiKey('')
      setTestResult(null)
      toast.success('AI provider settings saved')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save AI provider settings')
    } finally {
      setLlmSaving(false)
    }
  }

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const payload: {
        provider: LLMProvider
        base_url: string
        model: string
        api_key?: string
      } = {
        provider: llm.provider,
        base_url: llm.base_url,
        model: llm.model,
      }
      if (apiKey.trim()) {
        payload.api_key = apiKey.trim()
      }
      const res = await llmSettingsApi.test(payload)
      setTestResult({ success: res.data.success, message: res.data.message })
      // Sync the persisted indicator state from the backend.
      setLlm((prev) => ({
        ...prev,
        last_test_status: res.data.success ? 'ok' : 'failed',
        last_test_message: res.data.message,
        last_test_at: res.data.tested_at,
      }))
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err?.response?.data?.detail || 'Test request failed — is the backend running?',
      })
    } finally {
      setTesting(false)
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

        {/* AI Provider */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-200 mb-4">AI Provider</h2>

          {/* Status indicator — last known test result, shown on page load */}
          <div className="mb-4 flex items-center gap-2 text-sm">
            {llm.last_test_status === 'ok' ? (
              <span className="inline-flex items-center gap-1.5 text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Active — {LLM_PROVIDER_LABELS[llm.provider]} · {llm.model}
              </span>
            ) : llm.last_test_status === 'failed' ? (
              <span className="inline-flex items-center gap-1.5 text-red-400">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                {llm.last_test_message}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-gray-500">
                <span className="w-2 h-2 rounded-full bg-gray-500" />
                Not tested yet — {LLM_PROVIDER_LABELS[llm.provider]} · {llm.model}
              </span>
            )}
          </div>

          <p className="text-xs text-gray-500 mb-4">
            Which LLM processes your documents. OpenAI-compatible endpoints work with OpenAI,
            DeepSeek, OpenRouter, Groq and more. The API key is encrypted before storage and
            never shown again.
          </p>
          {llmLoading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-10 bg-dark-700 rounded" />
              <div className="h-10 bg-dark-700 rounded" />
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1.5">Provider</label>
                <select
                  value={llm.provider}
                  onChange={(e) => handleProviderChange(e.target.value as LLMProvider)}
                  className="input-field"
                >
                  {(Object.keys(LLM_PROVIDER_LABELS) as LLMProvider[]).map((p) => (
                    <option key={p} value={p} className="bg-dark-800">
                      {LLM_PROVIDER_LABELS[p]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1.5">API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="input-field"
                  placeholder={llm.has_api_key ? '•••••••• (saved — leave blank to keep)' : 'sk-...'}
                  autoComplete="off"
                />
                <p className="text-xs text-gray-500 mt-1.5">
                  {llm.has_api_key
                    ? 'A key is saved for this provider. Type a new one to replace it.'
                    : 'No key configured yet — documents will show a placeholder summary until one is added.'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1.5">Base URL</label>
                <input
                  type="text"
                  value={llm.base_url}
                  onChange={(e) => setLlm({ ...llm, base_url: e.target.value })}
                  className="input-field"
                  placeholder="https://api.openai.com/v1"
                />
                <p className="text-xs text-gray-500 mt-1.5">
                  {llm.provider === 'custom'
                    ? 'Required for custom endpoints (e.g. http://localhost:11434/v1 for Ollama).'
                    : 'Pre-filled with the default for this provider — editable if needed.'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1.5">Model</label>
                <input
                  type="text"
                  value={llm.model}
                  onChange={(e) => setLlm({ ...llm, model: e.target.value })}
                  className="input-field"
                  placeholder="gpt-4o-mini"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleTestConnection}
                  disabled={testing || llmSaving}
                  className="btn-primary !bg-dark-700 !border-dark-600 hover:!bg-dark-600 disabled:opacity-50"
                >
                  {testing ? 'Testing...' : 'Test Connection'}
                </button>
                <button
                  onClick={handleLlmSave}
                  disabled={llmSaving || testing}
                  className="btn-primary"
                >
                  {llmSaving ? 'Saving...' : 'Save AI Provider'}
                </button>
              </div>

              {/* Transient test result */}
              {testResult && (
                <div
                  className={`mt-3 text-sm rounded-lg px-3 py-2 border ${
                    testResult.success
                      ? 'text-emerald-300 border-emerald-800 bg-emerald-900/30'
                      : 'text-red-300 border-red-800 bg-red-900/30'
                  }`}
                >
                  {testResult.success ? '✓' : '✗'} {testResult.message}
                </div>
              )}
            </div>
          )}
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
