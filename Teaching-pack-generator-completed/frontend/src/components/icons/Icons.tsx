// Vintage Icon Components with beautiful gradients and styles

interface IconProps {
  className?: string;
  size?: number;
}

export const BookIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="bookGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#eab308" />
        <stop offset="100%" stopColor="#ca8a04" />
      </linearGradient>
    </defs>
    <path
      d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"
      stroke="url(#bookGradient)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
      stroke="url(#bookGradient)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="url(#bookGradient)"
      fillOpacity="0.1"
    />
    <path d="M9 6h8M9 10h8M9 14h5" stroke="url(#bookGradient)" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

export const UsersIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="usersGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#3b82f6" />
        <stop offset="100%" stopColor="#1d4ed8" />
      </linearGradient>
    </defs>
    <circle cx="9" cy="7" r="4" stroke="url(#usersGradient)" strokeWidth="2" fill="url(#usersGradient)" fillOpacity="0.2" />
    <path
      d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"
      stroke="url(#usersGradient)"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <circle cx="17" cy="7" r="3" stroke="url(#usersGradient)" strokeWidth="2" fill="url(#usersGradient)" fillOpacity="0.15" />
    <path d="M21 21v-1.5a3.5 3.5 0 0 0-3-3.5" stroke="url(#usersGradient)" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const PackageIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="packageGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#8b5cf6" />
        <stop offset="100%" stopColor="#6d28d9" />
      </linearGradient>
    </defs>
    <path
      d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"
      stroke="url(#packageGradient)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="url(#packageGradient)"
      fillOpacity="0.15"
    />
    <polyline points="3.27 6.96 12 12.01 20.73 6.96" stroke="url(#packageGradient)" strokeWidth="2" strokeLinejoin="round" />
    <line x1="12" y1="22.08" x2="12" y2="12" stroke="url(#packageGradient)" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const ActivityIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="activityGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#10b981" />
        <stop offset="100%" stopColor="#059669" />
      </linearGradient>
    </defs>
    <polyline
      points="22 12 18 12 15 21 9 3 6 12 2 12"
      stroke="url(#activityGradient)"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const HomeIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="homeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#eab308" />
        <stop offset="100%" stopColor="#ca8a04" />
      </linearGradient>
    </defs>
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="url(#homeGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#homeGradient)" fillOpacity="0.1" />
    <polyline points="9 22 9 12 15 12 15 22" stroke="url(#homeGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const CalendarIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="calendarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ec4899" />
        <stop offset="100%" stopColor="#db2777" />
      </linearGradient>
    </defs>
    <rect x="3" y="4" width="18" height="18" rx="2" stroke="url(#calendarGradient)" strokeWidth="2" fill="url(#calendarGradient)" fillOpacity="0.1" />
    <line x1="16" y1="2" x2="16" y2="6" stroke="url(#calendarGradient)" strokeWidth="2" strokeLinecap="round" />
    <line x1="8" y1="2" x2="8" y2="6" stroke="url(#calendarGradient)" strokeWidth="2" strokeLinecap="round" />
    <line x1="3" y1="10" x2="21" y2="10" stroke="url(#calendarGradient)" strokeWidth="2" strokeLinecap="round" />
    <circle cx="8" cy="15" r="1.5" fill="url(#calendarGradient)" />
    <circle cx="12" cy="15" r="1.5" fill="url(#calendarGradient)" />
    <circle cx="16" cy="15" r="1.5" fill="url(#calendarGradient)" />
  </svg>
);

export const SettingsIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="settingsGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#64748b" />
        <stop offset="100%" stopColor="#475569" />
      </linearGradient>
    </defs>
    <path opacity="0.34" d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="url(#settingsGradient)" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M2 12.8799V11.1199C2 10.0799 2.85 9.21994 3.9 9.21994C5.71 9.21994 6.45 7.93994 5.54 6.36994C5.02 5.46994 5.33 4.29994 6.24 3.77994L7.97 2.78994C8.76 2.31994 9.78 2.59994 10.25 3.38994L10.36 3.57994C11.26 5.14994 12.74 5.14994 13.65 3.57994L13.76 3.38994C14.23 2.59994 15.25 2.31994 16.04 2.78994L17.77 3.77994C18.68 4.29994 18.99 5.46994 18.47 6.36994C17.56 7.93994 18.3 9.21994 20.11 9.21994C21.15 9.21994 22.01 10.0699 22.01 11.1199V12.8799C22.01 13.9199 21.16 14.7799 20.11 14.7799C18.3 14.7799 17.56 16.0599 18.47 17.6299C18.99 18.5399 18.68 19.6999 17.77 20.2199L16.04 21.2099C15.25 21.6799 14.23 21.3999 13.76 20.6099L13.65 20.4199C12.75 18.8499 11.27 18.8499 10.36 20.4199L10.25 20.6099C9.78 21.3999 8.76 21.6799 7.97 21.2099L6.24 20.2199C5.33 19.6999 5.02 18.5299 5.54 17.6299C6.45 16.0599 5.71 14.7799 3.9 14.7799C2.85 14.7799 2 13.9199 2 12.8799Z" stroke="url(#settingsGradient)" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

export const BellIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="bellGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#eab308" />
        <stop offset="100%" stopColor="#ca8a04" />
      </linearGradient>
    </defs>
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="url(#bellGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#bellGradient)" fillOpacity="0.1" />
    <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="url(#bellGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const SearchIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="searchGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#64748b" />
        <stop offset="100%" stopColor="#475569" />
      </linearGradient>
    </defs>
    <circle cx="11" cy="11" r="8" stroke="url(#searchGradient)" strokeWidth="2" />
    <path d="m21 21-4.35-4.35" stroke="url(#searchGradient)" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const PlusIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <line x1="12" y1="5" x2="12" y2="19" stroke="black" strokeWidth="2.5" strokeLinecap="round" />
    <line x1="5" y1="12" x2="19" y2="12" stroke="black" strokeWidth="2.5" strokeLinecap="round" />
  </svg>
);

export const UploadIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="uploadGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#3b82f6" />
        <stop offset="100%" stopColor="#1d4ed8" />
      </linearGradient>
    </defs>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="url(#uploadGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <polyline points="17 8 12 3 7 8" stroke="url(#uploadGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="12" y1="3" x2="12" y2="15" stroke="url(#uploadGradient)" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const ChartIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="chartGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#8b5cf6" />
        <stop offset="100%" stopColor="#6d28d9" />
      </linearGradient>
    </defs>
    <line x1="18" y1="20" x2="18" y2="10" stroke="url(#chartGradient)" strokeWidth="2" strokeLinecap="round" />
    <line x1="12" y1="20" x2="12" y2="4" stroke="url(#chartGradient)" strokeWidth="2" strokeLinecap="round" />
    <line x1="6" y1="20" x2="6" y2="14" stroke="url(#chartGradient)" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const ReportIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <defs>
      <linearGradient id="reportGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ef4444" />
        <stop offset="100%" stopColor="#dc2626" />
      </linearGradient>
    </defs>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="url(#reportGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#reportGradient)" fillOpacity="0.1" />
    <polyline points="14 2 14 8 20 8" stroke="url(#reportGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="16" y1="13" x2="8" y2="13" stroke="url(#reportGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="16" y1="17" x2="8" y2="17" stroke="url(#reportGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <polyline points="10 9 9 9 8 9" stroke="url(#reportGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const SparklesIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="sparklesGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#fbbf24" />
        <stop offset="100%" stopColor="#eab308" />
      </linearGradient>
    </defs>
    <path d="M12 3l2 7 7 2-7 2-2 7-2-7-7-2 7-2z" fill="url(#sparklesGradient)" stroke="url(#sparklesGradient)" strokeWidth="1.5" strokeLinejoin="round" />
    <path d="M5 3l1 3 3 1-3 1-1 3-1-3-3-1 3-1z" fill="url(#sparklesGradient)" opacity="0.6" />
    <path d="M19 17l1 3 3 1-3 1-1 3-1-3-3-1 3-1z" fill="url(#sparklesGradient)" opacity="0.6" />
  </svg>
);

export const CheckCircleIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="checkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#10b981" />
        <stop offset="100%" stopColor="#059669" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" stroke="url(#checkGradient)" strokeWidth="2" fill="url(#checkGradient)" fillOpacity="0.15" />
    <polyline points="9 12 11 14 15 10" stroke="url(#checkGradient)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const InfoCircleIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="infoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#3b82f6" />
        <stop offset="100%" stopColor="#1d4ed8" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" stroke="url(#infoGradient)" strokeWidth="2" fill="url(#infoGradient)" fillOpacity="0.15" />
    <line x1="12" y1="16" x2="12" y2="12" stroke="url(#infoGradient)" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="12" cy="8" r="1" fill="url(#infoGradient)" />
  </svg>
);

export const WarningIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="warningGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#fbbf24" />
        <stop offset="100%" stopColor="#eab308" />
      </linearGradient>
    </defs>
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="url(#warningGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#warningGradient)" fillOpacity="0.15" />
    <line x1="12" y1="9" x2="12" y2="13" stroke="url(#warningGradient)" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="12" cy="17" r="1" fill="url(#warningGradient)" />
  </svg>
);

export const ErrorIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="errorGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ef4444" />
        <stop offset="100%" stopColor="#dc2626" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" stroke="url(#errorGradient)" strokeWidth="2" fill="url(#errorGradient)" fillOpacity="0.15" />
    <line x1="15" y1="9" x2="9" y2="15" stroke="url(#errorGradient)" strokeWidth="2.5" strokeLinecap="round" />
    <line x1="9" y1="9" x2="15" y2="15" stroke="url(#errorGradient)" strokeWidth="2.5" strokeLinecap="round" />
  </svg>
);

export const GridIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="gridGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#64748b" />
        <stop offset="100%" stopColor="#475569" />
      </linearGradient>
    </defs>
    <rect x="3" y="3" width="7" height="7" rx="1" stroke="url(#gridGradient)" strokeWidth="2" fill="url(#gridGradient)" fillOpacity="0.1" />
    <rect x="14" y="3" width="7" height="7" rx="1" stroke="url(#gridGradient)" strokeWidth="2" fill="url(#gridGradient)" fillOpacity="0.1" />
    <rect x="14" y="14" width="7" height="7" rx="1" stroke="url(#gridGradient)" strokeWidth="2" fill="url(#gridGradient)" fillOpacity="0.1" />
    <rect x="3" y="14" width="7" height="7" rx="1" stroke="url(#gridGradient)" strokeWidth="2" fill="url(#gridGradient)" fillOpacity="0.1" />
  </svg>
);

export const ListIcon = ({ className = "", size = 24 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="listGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#64748b" />
        <stop offset="100%" stopColor="#475569" />
      </linearGradient>
    </defs>
    <line x1="8" y1="6" x2="21" y2="6" stroke="url(#listGradient)" strokeWidth="2" strokeLinecap="round" />
    <line x1="8" y1="12" x2="21" y2="12" stroke="url(#listGradient)" strokeWidth="2" strokeLinecap="round" />
    <line x1="8" y1="18" x2="21" y2="18" stroke="url(#listGradient)" strokeWidth="2" strokeLinecap="round" />
    <circle cx="4" cy="6" r="1.5" fill="url(#listGradient)" />
    <circle cx="4" cy="12" r="1.5" fill="url(#listGradient)" />
    <circle cx="4" cy="18" r="1.5" fill="url(#listGradient)" />
  </svg>
);

export const HamburgerIcon = ({ className = "", size = 24, isOpen = false }: IconProps & { isOpen?: boolean }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="sidebarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#374151" />
        <stop offset="100%" stopColor="#1f2937" />
      </linearGradient>
    </defs>
    {isOpen ? (
      // Sidebar left icon (open)
      <path fillRule="evenodd" clipRule="evenodd" d="M6 4C4.34315 4 3 5.34315 3 7V17C3 18.6569 4.34315 20 6 20H18C19.6569 20 21 18.6569 21 17V7C21 5.34315 19.6569 4 18 4H6ZM5 7C5 6.44772 5.44772 6 6 6H9V18H6C5.44772 18 5 17.5523 5 17V7ZM11 18H18C18.5523 18 19 17.5523 19 17V7C19 6.44772 18.5523 6 18 6H11V18Z" fill="url(#sidebarGradient)"/>
    ) : (
      // Sidebar right icon (collapse)
      <path fillRule="evenodd" clipRule="evenodd" d="M6 4C4.34315 4 3 5.34315 3 7V17C3 18.6569 4.34315 20 6 20H18C19.6569 20 21 18.6569 21 17V7C21 5.34315 19.6569 4 18 4H6ZM5 7C5 6.44772 5.44772 6 6 6H13V18H6C5.44772 18 5 17.5523 5 17V7ZM15 18H18C18.5523 18 19 17.5523 19 17V7C19 6.44772 18.5523 6 18 6H15V18Z" fill="url(#sidebarGradient)"/>
    )}
  </svg>
);
