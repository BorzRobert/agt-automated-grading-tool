import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

describe('App routing', () => {
  it('renders the tutorial page on the /guide route and includes navigation to the grading page', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/guide']}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: /how to use the grading tool/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /upload form/i })).toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: /upload form/i }));
    expect(screen.getByRole('heading', { name: /automated grading tool/i })).toBeInTheDocument();
  });
});
