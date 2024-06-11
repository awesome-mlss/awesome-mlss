<p align="center">
  <a href="https://awesome-mlss.com/">
    <img src="https://awesome-mlss.com/static/img/favicon.png" width="320" alt="Awesome MLSS logo">
  </a>
</p>

<p align="center">
  <strong>
    Awesome MLSS
  </strong>
  <br>
    A community project to keep track of deadlines for Machine Learning Summer Schools (MLSS) around the world
</p>

<p align="center">
  <a href="https://x.com/awesomeMLSS">
    <img alt="X (formerly Twitter) Follow" src="https://img.shields.io/twitter/follow/awesomeMLSS">
  </a>
  <a href="https://github.com/sshkhr/awesome-mlss/pulse" alt="Activity">
        <img src="https://img.shields.io/github/commit-activity/m/sshkhr/awesome-mlss" />
  </a>  
  <a href="https://github.com/sshkhr/awesome-mlss">
    <img src="https://img.shields.io/badge/Contributions-Welcome-brightgreen" alt="Contributions Welcome">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
  </a>
  <a href="https://awesome-mlss.com">
    <img src="https://github.com/sshkhr/dlai-companion/actions/workflows/pages/pages-build-deployment/badge.svg" alt="GitHub Pages">
  </a>
  <a href="https://github.com/sshkhr/awesome-mlss/stargazers">
    <img src="https://img.shields.io/github/stars/sshkhr/awesome-mlss" alt="GitHub Stars">
  </a>
</p>

[awesome-mlss.com](https://awesome-mlss.com/) is a community tool which serves as a central repository for deadlines of calls for participation at summer schools in machine learning and other closely related fields.

> <details>
>      <summary><strong> 🧐 Wait, what happened to the old README.MD with the list of schools? </strong></font></summary>
>      The old README which contained the list of all summer schools in a markdown format has been moved to the <a href="OLD_README.md">OLD_README.md</a> file.
>      We do not plan to maintain the old list anymore, but if you want to contribute to both the new list and the old list you are more than welcome to do so.<br><br>
>      We believe that a website format with deadlines and calendar links suits our project better, and we hope you will find it more useful as well.
> </details>

## Contributing

Contributions are very welcome!

To add or update a new summer school deadline:
- Fork the repository
- Optional: create a new branch with the name of the summer school
- Update `_data/summerschools.yml`
- Make sure it has the `title`, `year`, `id`, `link`, `deadline`, `timezone`, `date`, `place`, `sub` attributes
    + See available timezone strings [here](https://momentjs.com/timezone/).
- Optionally add a `note` in case there is important information to convey
- Example:
    ```yaml
    - title: BestMLSS
      year: 2022
      id: bestmlss22  # title as lower case + last two digits of year
      full_name: Best Machine Learning Summer School # full conference name
      link: link-to-website.com
      deadline: YYYY-MM-DD HH:SS
      abstract_deadline: YYYY-MM-DD HH:SS
      timezone: Asia/Seoul
      place: Incheon, South Korea
      date: September, 18-22, 2022
      start: YYYY-MM-DD
      end: YYYY-MM-DD
      sub: SP
      note: Important
    ```
- Send a pull request

## Acknowledgements

The awesome-mlss website was built upon the amazing work done by:

- [https://aideadlin.es/][1] by [@abhshkdz](https://twitter.com/abhshkdz) and [Papers With Code](https://paperswithcode.com/)
- [pythondeadlin.es][2] by [@jesperdramsch](https://dramsch.net/)

## License

This project is licensed under [MIT][1].

It uses:

- [IcoMoon Icons](https://icomoon.io/#icons-icomoon): [GPL](http://www.gnu.org/licenses/gpl.html) / [CC BY4.0](http://creativecommons.org/licenses/by/4.0/)


[1]: http://aideadlin.es/
[2]: https://pythondeadlin.es/