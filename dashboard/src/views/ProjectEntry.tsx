import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import NewProject from './NewProject';
import TrialProject from './TrialProject';

const ProjectEntry: React.FC = () => {
  const { access } = useAuth();
  return access?.isAdmin ? <NewProject /> : <TrialProject />;
};

export default ProjectEntry;
