using Auth0.OidcClient;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using WPFMediaKit.DirectShow.Controls;
using WPFMediaKit.DirectShow.MediaPlayers;

namespace GGShot
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        private MainWindowViewModel m_viewModel;

        public MainWindow()
        {
            InitializeComponent();
            m_viewModel = new MainWindowViewModel();
            DataContext = m_viewModel;
            m_viewModel.MediaElement = mediaElement;
            //m_viewModel.SetFile(@"C:\Users\timmi\Videos\Captures\ASTRONEER 2020-03-19 22-05-10.mp4");

            //m_viewModel.DoLogon();
        }
    }
}
