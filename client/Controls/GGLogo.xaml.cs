using System;
using System.Collections.Generic;
using System.Diagnostics;
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

namespace GGShot.Controls
{
    /// <summary>
    /// Interaction logic for GGLogo.xaml
    /// </summary>
    public partial class GGLogo : UserControl
    {
        public GGLogo()
        {
            InitializeComponent();
        }

        private void Image_MouseDown(object sender, MouseButtonEventArgs e)
        {
            Process.Start("https://gameshots.gg");
        }
    }
}
