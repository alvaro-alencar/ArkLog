import React from 'react';

const GithubIcon = ({ size = 20 }: { size?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
  </svg>
);

const Login: React.FC = () => {
  const handleGithubLogin = () => {
    window.location.href = '/api/v1/auth/login/github';
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <div className="max-w-md w-full text-center space-y-8">
        <div className="space-y-2">
          <img src="/logo_arklog.png" alt="ArkLog" className="h-40 w-auto mx-auto" />
          <p className="text-gray-400">AI-powered progress reporter for modern teams.</p>
        </div>
        
        <div className="glass-card p-8 space-y-6 bg-[#0a0a0a]">
          <h2 className="text-xl font-medium text-white">Get started</h2>
          <p className="text-sm text-gray-400">
            Sign in with your GitHub account to manage your projects and view reports.
          </p>
          <button
            onClick={handleGithubLogin}
            className="w-full flex items-center justify-center gap-3 bg-white text-black py-2.5 px-4 rounded-md font-medium transition-transform active:scale-[0.98] hover:bg-gray-200"
          >
            <GithubIcon size={20} />
            Continue with GitHub
          </button>
        </div>

        <p className="text-xs text-gray-500">
          By continuing, you agree to ArkLog's Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
};

export default Login;
