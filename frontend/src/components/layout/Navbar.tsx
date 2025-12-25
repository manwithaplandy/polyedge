'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/' },
  { name: 'Signals', href: '/signals' },
  { name: 'Markets', href: '/markets' },
  { name: 'Track Record', href: '/track-record' },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-zinc-800 bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">PE</span>
              </div>
              <span className="text-xl font-bold text-white">PolyEdge</span>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:block">
            <div className="flex items-center space-x-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-zinc-800 text-white'
                        : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                    )}
                  >
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* CTA Button */}
          <div className="flex items-center gap-4">
            <Link
              href="#alerts"
              className="hidden sm:inline-flex items-center px-4 py-2 rounded-md text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-500 transition-colors"
            >
              Get Alerts
            </Link>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden border-t border-zinc-800">
        <div className="flex justify-around py-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'px-3 py-2 text-xs font-medium transition-colors',
                  isActive ? 'text-emerald-500' : 'text-zinc-400'
                )}
              >
                {item.name}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
