import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ─── InputArea ─────────────────────────────────────────────────
import InputArea from '../components/InputArea.jsx';

describe('InputArea', () => {
  it('renders textarea and send button', () => {
    render(<InputArea onSend={() => {}} disabled={false} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByLabelText('Send message')).toBeInTheDocument();
  });

  it('send button is disabled when input is empty', () => {
    render(<InputArea onSend={() => {}} disabled={false} />);
    expect(screen.getByLabelText('Send message')).toBeDisabled();
  });

  it('calls onSend with trimmed text and clears input', async () => {
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} disabled={false} />);
    const textarea = screen.getByRole('textbox');

    await userEvent.type(textarea, '  Hello world  ');
    await userEvent.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledWith('Hello world');
    expect(textarea.value).toBe('');
  });

  it('does not send on Shift+Enter', async () => {
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} disabled={false} />);
    const textarea = screen.getByRole('textbox');

    await userEvent.type(textarea, 'test');
    await userEvent.keyboard('{Shift>}{Enter}{/Shift}');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('shows cancel button when onCancel is provided', () => {
    const onCancel = vi.fn();
    render(<InputArea onSend={() => {}} disabled={true} onCancel={onCancel} />);
    expect(screen.getByLabelText('Stop generating')).toBeInTheDocument();
  });

  it('shows character count when typing', async () => {
    render(<InputArea onSend={() => {}} disabled={false} />);
    const textarea = screen.getByRole('textbox');

    await userEvent.type(textarea, 'Hello');
    expect(screen.getByText('1995')).toBeInTheDocument();
  });

  it('prevents input beyond max length', async () => {
    render(<InputArea onSend={() => {}} disabled={false} />);
    const textarea = screen.getByRole('textbox');

    const longText = 'x'.repeat(2001);
    fireEvent.change(textarea, { target: { value: longText } });
    // Should not update since it exceeds MAX_LENGTH
    expect(textarea.value).toBe('');
  });
});

// ─── WelcomeScreen ────────────────────────────────────────────
import WelcomeScreen from '../components/WelcomeScreen.jsx';

describe('WelcomeScreen', () => {
  it('renders InferaMind AI heading', () => {
    render(<WelcomeScreen onSuggestionClick={() => {}} />);
    expect(screen.getByText('InferaMind AI')).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(<WelcomeScreen onSuggestionClick={() => {}} />);
    expect(screen.getByText('Ask me anything about the ML course videos')).toBeInTheDocument();
  });

  it('renders suggestion buttons', () => {
    render(<WelcomeScreen onSuggestionClick={() => {}} />);
    expect(screen.getByText('What is supervised learning?')).toBeInTheDocument();
    expect(screen.getByText('Explain gradient descent simply')).toBeInTheDocument();
  });

  it('calls onSuggestionClick when suggestion is clicked', async () => {
    const onClick = vi.fn();
    render(<WelcomeScreen onSuggestionClick={onClick} />);

    await userEvent.click(screen.getByText('What is supervised learning?'));
    expect(onClick).toHaveBeenCalledWith('What is supervised learning?');
  });

  it('renders suggestions label', () => {
    render(<WelcomeScreen onSuggestionClick={() => {}} />);
    expect(screen.getByText('Suggestions')).toBeInTheDocument();
  });
});

// ─── ErrorBoundary ────────────────────────────────────────────
import ErrorBoundary from '../components/ErrorBoundary.jsx';

function ThrowError() {
  throw new Error('Test crash');
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <p>All good</p>
      </ErrorBoundary>
    );
    expect(screen.getByText('All good')).toBeInTheDocument();
  });

  it('renders fallback UI on error', () => {
    // Suppress console.error for expected error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test crash')).toBeInTheDocument();
    spy.mockRestore();
  });

  it('shows Try Again button on error', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    const btn = screen.getByText('Try Again');
    expect(btn).toBeInTheDocument();
    spy.mockRestore();
  });
});

// ─── PipelineStatus ───────────────────────────────────────────
import PipelineStatus from '../components/PipelineStatus.jsx';

describe('PipelineStatus', () => {
  it('renders nothing when no activeNode', () => {
    const { container } = render(<PipelineStatus activeNode={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders all 3 nodes', () => {
    render(<PipelineStatus activeNode="classify" />);
    expect(screen.getByText('Classify')).toBeInTheDocument();
    expect(screen.getByText('Retrieve')).toBeInTheDocument();
    expect(screen.getByText('Generate')).toBeInTheDocument();
  });

  it('marks classify as active when activeNode is classify', () => {
    render(<PipelineStatus activeNode="classify" />);
    const classifyNode = screen.getByLabelText('Classify: active');
    expect(classifyNode).toHaveClass('active');
  });

  it('marks classify as done when activeNode is retrieve', () => {
    render(<PipelineStatus activeNode="retrieve" />);
    expect(screen.getByLabelText('Classify: done')).toHaveClass('done');
    expect(screen.getByLabelText('Retrieve: active')).toHaveClass('active');
  });
});

// ─── SourceCard ───────────────────────────────────────────────
import SourceCard from '../components/SourceCard.jsx';

describe('SourceCard', () => {
  const mockSources = [
    { video: 1, start: 90, end: 120, text: 'Machine learning is...', similarity: 0.85 },
    { video: 2, start: 200, end: 230, text: 'Supervised learning...', similarity: 0.72 },
  ];

  it('renders nothing when sources is empty', () => {
    const { container } = render(<SourceCard sources={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when sources is null', () => {
    const { container } = render(<SourceCard sources={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows correct number of sources', () => {
    render(<SourceCard sources={mockSources} />);
    expect(screen.getByText('Sources (2 chunks)')).toBeInTheDocument();
  });

  it('displays video numbers', () => {
    render(<SourceCard sources={mockSources} />);
    expect(screen.getByText('Video 1')).toBeInTheDocument();
    expect(screen.getByText('Video 2')).toBeInTheDocument();
  });

  it('formats timestamps correctly', () => {
    render(<SourceCard sources={mockSources} />);
    expect(screen.getByText('1:30 - 2:00')).toBeInTheDocument();
    expect(screen.getByText('3:20 - 3:50')).toBeInTheDocument();
  });

  it('shows similarity scores as percentages', () => {
    render(<SourceCard sources={mockSources} />);
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
  });

  it('color-codes high similarity', () => {
    render(<SourceCard sources={mockSources} />);
    expect(screen.getByText('85%')).toHaveClass('high');
    expect(screen.getByText('72%')).toHaveClass('high');
  });
});
