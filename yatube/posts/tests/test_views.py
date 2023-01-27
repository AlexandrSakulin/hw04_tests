from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from django import forms

from ..models import Group, Post, User

TEST_POST_TEXT = 'Тестовый пост №13 тестового пользователя в тестовой группе'


class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text=TEST_POST_TEXT,
        )

    def setUp(self):
        self.auth_client = Client()

        self.auth_client.force_login(PostsViewsTests.user)

    def test_posts_show_correct_context(self):
        """Шаблоны posts сформированы с правильным контекстом."""
        name_list = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:group_list', args=(self.group.slug,)): 'page_obj',
            reverse('posts:profile', args=(self.user.username,)): 'page_obj',
            reverse('posts:post_detail', args=(self.post.pk,)): 'post',
        }
        for reverse_name, context in name_list.items():
            first_object = self.client.get(reverse_name)
            if context == 'post':
                first_object = first_object.context[context]
            else:
                first_object = first_object.context[context][0]
            post_text = first_object.text
            post_author = first_object.author
            post_group = first_object.group
            posts_dict = {
                post_text: self.post.text,
                post_author: self.user,
                post_group: self.group,
            }
            for post_param, test_post_param in posts_dict.items():
                with self.subTest(
                        post_param=post_param,
                        test_post_param=test_post_param):
                    self.assertEqual(post_param, test_post_param)

    def test_post_create_and_edit_show_correct_context(self):
        """Шаблон create_post (create) and (edit) сформирован
        с правильным контекстом."""
        namespace = {
            reverse('posts:post_create'),
            reverse('posts:post_edit', args=(self.post.pk,)),
        }
        for reverse_name in namespace:
            response = self.auth_client.get(reverse_name)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_correct_not_appear(self):
        """Проверка, что созданный пост не появляется в группе """
        """к которой он не принадлежит."""

        response = self.auth_client.get(
            reverse('posts:group_list', args=(self.group.slug,))
        )
        context_post = response.context['page_obj'][0]
        self.assertNotEqual(context_post, 'Тестовый пост №')

    def test_post_with_group_on_pages(self):
        """Если указать группу при создании то пост появиться
        на главной, в группе и профайле"""

        templates_pages_names = {
            reverse("posts:index"):
                'posts/index.html',
            reverse("posts:group_list", args=(self.group.slug,)):
                'posts/group_list.html',
            reverse("posts:profile", args=(self.user.username,)):
                'posts/profile.html',
        }

        for reverse_name, _ in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.auth_client.get(reverse_name)
                self.assertIn(
                    self.post, response.context['page_obj']
                )


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='test-author')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Описание тестовой группы'
        )
        post_list = []
        for i in range(0, 13):
            new_post = Post(
                text=f'Тестовый пост контент {i}',
                group=cls.group,
                author=cls.user
            )
            post_list.append(new_post)
        Post.objects.bulk_create(post_list)

    def test_first_page(self):
        """Тестируем первую страницу пагинатора."""

        page_list = [
            reverse('posts:index'),
            reverse('posts:group_list', args=(self.group.slug,)),
            reverse('posts:profile', args=(self.user.username,))
        ]
        for page in page_list:
            response = self.authorized_client.get(page)
            self.assertEqual(
                len(response.context['page_obj']), settings.POSTS_IN_PAGE
            )

    def test_second_page(self):
        """Тестируем вторую страницу пагинатора."""
        slug = self.group.slug
        username = self.user.username
        page_list = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': slug}),
            reverse('posts:profile', kwargs={'username': username})
        }
        count_posts = Post.objects.count()
        count = count_posts - settings.POSTS_IN_PAGE
        for page in page_list:
            response = self.authorized_client.get(page + '?page=2')
            self.assertEqual(len(response.context['page_obj']), count)
