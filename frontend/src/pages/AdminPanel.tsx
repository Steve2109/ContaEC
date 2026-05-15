import React from 'react';
import { useStore } from '../store/useStore';

const AdminPanel: React.FC = () => {
  const { user } = useStore();
  
  if (!user?.is_admin) {
    return <div className="text-red-600">Acceso denegado. Solo administradores.</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Panel de Administrador</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm">
          <h3 className="font-semibold mb-2">Usuarios</h3>
          <p className="text-3xl font-bold text-primary-600">--</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm">
          <h3 className="font-semibold mb-2">Licencias Activas</h3>
          <p className="text-3xl font-bold text-green-600">--</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm">
          <h3 className="font-semibold mb-2">Licencias por Vencer</h3>
          <p className="text-3xl font-bold text-yellow-600">--</p>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
