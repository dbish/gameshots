using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Input;

namespace GGShot.Util
{
    public class DelegateCommand : ICommand
    {
        readonly Action m_execute;
        readonly Func<bool> m_canExecute;

        public event EventHandler CanExecuteChanged;

        public DelegateCommand(Action executeMethod)
            : this(executeMethod, () => true)
        {
        }

        public DelegateCommand(Action executeMethod, Func<bool> canExecuteMethod)
        {
            m_execute = executeMethod;
            m_canExecute = canExecuteMethod;
        }

        public bool CanExecute(object parameter)
        {
            return m_canExecute();
        }

        public void RaiseCanExecuteChanged()
        {
            CanExecuteChanged?.Invoke(this, new EventArgs());
        }

        public void Execute(object parameter)
        {
            m_execute();
        }

        public void Execute()
        {
            m_execute();
        }

        public bool CanExecute()
        {
            return m_canExecute();
        }
    }
}
