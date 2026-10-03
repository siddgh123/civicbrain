import { render, screen, within } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from './App';
import { routes } from './app/routes';
import type { AuthState, Role } from './auth/authContext';

function renderAt(path: string, auth?: AuthState) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} initialAuth={auth} />);
  return router;
}

function signedIn(role: Role): AuthState {
  return {
    accessToken: 'test-token',
    user: { id: 7, fullName: 'Test User', role, mustChangePassword: false, preferredLanguage: 'en' },
  };
}

describe('App routing', () => {
  it('/ renders the landing heading and the three main actions', async () => {
    renderAt('/');

    expect(
      await screen.findByRole('heading', { level: 1, name: /report civic problems/i }),
    ).toBeInTheDocument();
    const main = screen.getByRole('main');
    expect(within(main).getByRole('link', { name: 'Report a problem' })).toHaveAttribute('href', '/citizen/new');
    expect(within(main).getByRole('link', { name: 'Track my complaint' })).toHaveAttribute(
      'href',
      '/citizen/complaints',
    );
    expect(within(main).getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login');
  });

  it('an unknown route shows the 404 page', async () => {
    renderAt('/no-such-page');

    expect(await screen.findByRole('heading', { level: 1, name: 'Page not found' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to the start page' })).toHaveAttribute('href', '/');
  });

  it('/officer without login redirects to /login with the return URL', async () => {
    const router = renderAt('/officer');

    expect(await screen.findByRole('heading', { level: 1, name: 'Log in' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/login');
    expect(new URLSearchParams(router.state.location.search).get('returnTo')).toBe('/officer');
  });

  it('a track link from a message asks for login first and keeps the complaint number', async () => {
    const router = renderAt('/c/CB-000123');

    expect(await screen.findByRole('heading', { level: 1, name: 'Log in' })).toBeInTheDocument();
    expect(new URLSearchParams(router.state.location.search).get('returnTo')).toBe('/c/CB-000123');
  });

  it('a citizen who opens /officer sees the no-access page, not the officer portal', async () => {
    renderAt('/officer', signedIn('CITIZEN'));

    expect(await screen.findByRole('heading', { level: 1, name: 'No access' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).not.toBeInTheDocument();
    expect(within(screen.getByRole('main')).getByRole('link', { name: 'Go to my start page' })).toHaveAttribute(
      'href',
      '/citizen',
    );
  });

  it('an officer gets the officer layout with the left navigation (no Admin entry)', async () => {
    renderAt('/officer', signedIn('OFFICER'));

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' });
    for (const name of ['Dashboard', 'Complaints', 'Action plans', 'Contractors']) {
      expect(within(nav).getByRole('link', { name })).toBeInTheDocument();
    }
    expect(within(nav).queryByRole('link', { name: 'Admin' })).not.toBeInTheDocument();
  });

  it('an officer who opens /officer/admin sees "No access" inside the officer layout', async () => {
    renderAt('/officer/admin', signedIn('OFFICER'));

    expect(await screen.findByRole('heading', { level: 1, name: 'No access' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
  });

  it('an admin also sees the Admin entry', async () => {
    renderAt('/officer', signedIn('ADMIN'));

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' });
    expect(within(nav).getByRole('link', { name: 'Admin' })).toHaveAttribute('href', '/officer/admin');
  });

  it('a citizen gets the mobile layout with the bottom navigation', async () => {
    renderAt('/citizen', signedIn('CITIZEN'));

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' });
    for (const name of ['Home', 'Report', 'My complaints']) {
      expect(within(nav).getByRole('link', { name })).toBeInTheDocument();
    }
  });
});
