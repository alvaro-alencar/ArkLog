import React from 'react';
import { Columns3, GitBranch, ListChecks, MessageSquare, NotebookTabs, Plug } from 'lucide-react';

const ProviderIcon: React.FC<{ provider: string; size?: number }> = ({ provider, size = 20 }) => {
  if (provider === 'github') return <GitBranch size={size} />;
  if (provider === 'slack') return <MessageSquare size={size} />;
  if (provider === 'notion') return <NotebookTabs size={size} />;
  if (provider === 'clickup') return <ListChecks size={size} />;
  if (provider === 'trello') return <Columns3 size={size} />;
  return <Plug size={size} />;
};

export default ProviderIcon;
