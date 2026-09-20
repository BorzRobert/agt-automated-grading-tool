import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import { UploadForm } from './components/UploadForm';

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

  it('prefills the fill threshold with 0.5', () => {
    render(
      <MemoryRouter>
        <UploadForm />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText(/fill threshold/i)).toHaveValue(0.5);
  });

  it('renders the blank template generator on its own route', () => {
    render(
      <MemoryRouter initialEntries={['/template']}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: /generate a blank template/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /blank template/i })).toHaveClass('active');
    expect(screen.getByRole('link', { name: /upload form/i })).not.toHaveClass('active');
    expect(screen.queryByRole('heading', { name: /automated grading tool/i })).not.toBeInTheDocument();
  });
});
