import React from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { KeyValueList } from '../components/common/KeyValueList';
import { Check, ShieldAlert } from 'lucide-react';

export const SecurityPage: React.FC = () => {
  const isApiKeyConfigured = Boolean(
    (typeof window !== 'undefined' && localStorage.getItem('ent_api_key')) ||
    (import.meta.env.VITE_API_KEY as string)
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security & Governance Posture"
        description="Operator permissions, credential hygiene, and audit integrity controls."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel title="Authentication & Session Context">
          <KeyValueList
            items={[
              {
                label: 'Auth Method',
                value: 'API Key (Bearer Header / Query Ticket)',
              },
              {
                label: 'Credential Configured',
                value: isApiKeyConfigured ? (
                  <span className="inline-flex items-center gap-1 text-ok font-medium">
                    <Check className="w-3.5 h-3.5" />
                    <span>Configured in Local Storage</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-warn font-medium">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Using Default Development Fallback</span>
                  </span>
                ),
              },
              {
                label: 'Active Role',
                value: 'Operations Controller / Shift Supervisor',
              },
              {
                label: 'Governed Permissions',
                value: 'Read Workflows, Approve Exceptions, Anchor Audit',
              },
            ]}
          />
        </Panel>

        <Panel title="WebSocket Ticket & Redaction Policy">
          <div className="space-y-3 text-[13px] text-text-2">
            <p>
              <strong className="text-text font-medium">WebSocket Ticket:</strong> Short-lived, single-use; stored in process memory. Multi-instance cluster deployments require a shared Redis or Postgres ticket state store.
            </p>
            <p>
              <strong className="text-text font-medium">Redaction Policy:</strong> Raw API credentials, customer personally identifiable information (PII), and financial settlement private keys are strictly stripped before persisting to the audit log or streaming over event channels.
            </p>
          </div>
        </Panel>
      </div>

      <Panel title="Credential Hygiene Checklist">
        <div className="divide-y divide-border text-[13px]">
          <div className="py-2.5 flex items-start gap-3">
            <span className="w-5 h-5 rounded-[4px] bg-ok-soft text-ok flex items-center justify-center shrink-0 mt-0.5">
              <Check className="w-3.5 h-3.5" />
            </span>
            <div>
              <div className="font-medium text-text">Environment Isolation</div>
              <div className="text-text-2 text-[12px]">
                API keys and connection strings live in local environment files (.env) only and are never committed to revision control.
              </div>
            </div>
          </div>

          <div className="py-2.5 flex items-start gap-3">
            <span className="w-5 h-5 rounded-[4px] bg-ok-soft text-ok flex items-center justify-center shrink-0 mt-0.5">
              <Check className="w-3.5 h-3.5" />
            </span>
            <div>
              <div className="font-medium text-text">Key Rotation Protocol</div>
              <div className="text-text-2 text-[12px]">
                Rotate operator credentials immediately if shared, logged, or exposed in client bundles.
              </div>
            </div>
          </div>

          <div className="py-2.5 flex items-start gap-3">
            <span className="w-5 h-5 rounded-[4px] bg-ok-soft text-ok flex items-center justify-center shrink-0 mt-0.5">
              <Check className="w-3.5 h-3.5" />
            </span>
            <div>
              <div className="font-medium text-text">Sepolia Testnet Key Safety</div>
              <div className="text-text-2 text-[12px]">
                Blockchain transaction signer uses a dedicated low-balance test account; mainnet accounts are prohibited in test environments.
              </div>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
};
