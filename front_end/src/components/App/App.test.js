import { render, screen } from '@testing-library/react';
import App from '.';

test('renders main container', () => {
  render(<App />);
  const mainElement = screen.getByRole('main');
  expect(mainElement).toBeInTheDocument();
});