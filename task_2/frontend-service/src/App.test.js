import { render, screen } from '@testing-library/react';
import App from './App';

test('renders microservices dashboard', () => {
  render(<App />);
  const linkElement = screen.getByText(/microservices dashboard/i);
  expect(linkElement).toBeInTheDocument();
});