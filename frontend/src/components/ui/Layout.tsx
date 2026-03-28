import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

/** App shell layout with sidebar and main content area. */
export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
