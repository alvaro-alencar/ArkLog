import React from 'react';
import { Columns3, GitBranch, ListChecks, MessageSquare, NotebookTabs, Plug } from 'lucide-react';

const monograms: Record<string, string> = {
  'gitlab': 'GL',
  'bitbucket': 'BB',
  'azure-devops': 'AZ',
  'jira': 'JR',
  'linear': 'LN',
  'asana': 'AS',
  'monday': 'MO',
  'google-drive': 'GD',
  'google-calendar': 'GC',
  'confluence': 'CF',
  'airtable': 'AT',
  'microsoft-teams': 'MT',
  'discord': 'DS',
  'hubspot': 'HS',
  'salesforce': 'SF',
  'zendesk': 'ZD',
  'intercom': 'IC',
  'sentry': 'SE',
  'datadog': 'DD',
  'vercel': '▲',
};

const ProviderIcon: React.FC<{ provider: string; size?: number }> = ({ provider, size = 20 }) => {
  if (provider === 'github') return <GitBranch size={size} />;
  if (provider === 'slack') return <MessageSquare size={size} />;
  if (provider === 'notion') return <NotebookTabs size={size} />;
  if (provider === 'clickup') return <ListChecks size={size} />;
  if (provider === 'trello') return <Columns3 size={size} />;
  if (monograms[provider]) {
    return <span className="font-black tracking-[-0.08em]" style={{ fontSize: Math.max(11, size * 0.48) }}>{monograms[provider]}</span>;
  }
  return <Plug size={size} />;
};

export default ProviderIcon;
