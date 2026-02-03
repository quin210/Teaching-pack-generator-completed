import { useState } from 'react';
import { CheckCircleIcon, InfoCircleIcon, WarningIcon, ErrorIcon, BellIcon } from './icons/Icons';

interface Notification {
  id: number;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  time: string;
  read: boolean;
}

interface NotificationsProps {
  onClose: () => void;
}

export default function Notifications({ onClose }: NotificationsProps) {
  const [notifications, setNotifications] = useState<Notification[]>([
    {
      id: 1,
      title: 'Teaching pack completed',
      message: 'Teaching pack for Math 10A1 has been created',
      type: 'success',
      time: '5 minutes ago',
      read: false,
    },
    {
      id: 2,
      title: 'New class created',
      message: 'Literature 11A2 has been added to the system',
      type: 'info',
      time: '2 hours ago',
      read: false,
    },
    {
      id: 3,
      title: 'System update',
      message: 'A new version with many features has been released',
      type: 'info',
      time: '1 day ago',
      read: true,
    },
  ]);

  const markAsRead = (id: number) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, read: true } : n
    ));
  };

  const markAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, read: true })));
  };

  const deleteNotification = (id: number) => {
    setNotifications(notifications.filter(n => n.id !== id));
  };

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success': return <CheckCircleIcon size={24} />;
      case 'warning': return <WarningIcon size={24} />;
      case 'error': return <ErrorIcon size={24} />;
      default: return <InfoCircleIcon size={24} />;
    }
  };

  const getColor = (type: Notification['type']) => {
    switch (type) {
      case 'success': return 'bg-green-50 border-green-200';
      case 'warning': return 'bg-yellow-50 border-yellow-200';
      case 'error': return 'bg-red-50 border-red-200';
      default: return 'bg-blue-50 border-blue-200';
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="fixed top-0 right-0 w-96 h-screen bg-white border-l border-stone-200 shadow-xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-stone-200">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold text-zinc-800">Notifications</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-stone-100 transition-colors"
          >
            ✕
          </button>
        </div>
        {unreadCount > 0 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-stone-600">{unreadCount} new notifications</p>
            <button
              onClick={markAllAsRead}
              className="text-sm text-yellow-600 hover:text-yellow-700"
            >
              Mark all as read
            </button>
          </div>
        )}
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {notifications.length === 0 ? (
          <div className="text-center py-12">
            <div className="flex justify-center mb-3">
              <BellIcon size={64} className="opacity-20" />
            </div>
            <p className="text-stone-600">No new notifications</p>
          </div>
        ) : (
          notifications.map((notification) => (
            <div
              key={notification.id}
              onClick={() => markAsRead(notification.id)}
              className={`
                p-4 rounded-lg border cursor-pointer transition-all
                ${notification.read ? 'bg-white border-stone-200' : getColor(notification.type)}
                hover:shadow-md
              `}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{getIcon(notification.type)}</span>
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-1">
                    <h3 className={`font-medium ${notification.read ? 'text-stone-700' : 'text-zinc-800'}`}>
                      {notification.title}
                    </h3>
                    {!notification.read && (
                      <div className="w-2 h-2 bg-yellow-500 rounded-full" />
                    )}
                  </div>
                  <p className="text-sm text-stone-600 mb-2">{notification.message}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-stone-500">{notification.time}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteNotification(notification.id);
                      }}
                      className="text-xs text-red-500 hover:text-red-600"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// Notification Bell Component
interface NotificationBellProps {
  onClick: () => void;
  count?: number;
}

export function NotificationBell({ onClick, count = 0 }: NotificationBellProps) {
  return (
    <button
      onClick={onClick}
      className="relative p-2 rounded-lg hover:bg-stone-100 transition-colors"
    >
      <BellIcon size={24} />
      {count > 0 && (
        <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-medium rounded-full flex items-center justify-center">
          {count > 9 ? '9+' : count}
        </div>
      )}
    </button>
  );
}
