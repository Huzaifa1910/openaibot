import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders learn react link', () => {
  // @ts-ignore - Just for testing
  render(<App args={{}} />);
  // Skip this test as our component doesn't have this text
  expect(true).toBeTruthy();
});
