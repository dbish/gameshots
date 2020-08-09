using Microsoft.WindowsAPICodePack.Shell;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace GGShot
{
    class BrowseItemViewModel
    {
        private string m_fileName;

        public BrowseItemViewModel(string fileName)
        {
            m_fileName = fileName;
        }

        public string FileName => m_fileName;

        public object ItemSource
        {
            get
            {
                if (m_fileName.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
                {
                    return new Uri(m_fileName);
                }
                else
                {
                    var sf = ShellFile.FromFilePath(m_fileName);
                    return sf.Thumbnail.ExtraLargeBitmapSource;
                }
            }
        }
    }
}
