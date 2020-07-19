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

        public Uri ItemSource => new Uri(m_fileName);
    }
}
