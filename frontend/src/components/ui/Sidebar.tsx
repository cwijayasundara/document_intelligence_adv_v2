import { NavLink } from "react-router-dom";
import { APP_NAME } from "../../lib/config";

interface NavItem {
  label: string;
  to: string;
}

const navItems: NavItem[] = [
  { label: "Dashboard", to: "/" },
  { label: "Upload", to: "/upload" },
  { label: "Categories", to: "/config/categories" },
  { label: "Extraction Fields", to: "/config/extraction-fields" },
  { label: "Bulk Processing", to: "/bulk" },
];

/** Sidebar navigation component. */
export default function Sidebar() {
  return (
    <aside className="w-64 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-lg font-heading font-semibold text-primary-500">
          {APP_NAME}
        </h1>
      </div>
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary-50 text-primary-700"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
